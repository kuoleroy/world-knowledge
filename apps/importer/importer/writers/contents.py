"""写入库：把自撰 MDX 导语幂等 upsert 到 Directus ``/items/contents``（任务书 05）。

复用 03 的 Directus REST 通道（写入口唯一、权限归 Directus、importer 不持库凭据）。

与 ``nodes`` 不同，``contents`` 以 ``node``（= ``nodes.id``，整数外键）为业务键，
**每节点只保留 1 条**——重复跑只 PATCH 有差异字段；正文（``body_ref``）变化时才把
``version`` 单调递增 +1，供下游 ``sort=-version, limit=1`` 取最新版。

**主控裁定**：AI 改写稿一律 ``status='draft'``，且仅在「新建」时写入；后续人工 /
社区审校把状态转成 ``published`` 之后，复跑绝不回退（``status`` 不纳入差异比对字段）。
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

import httpx

from .directus import (
    BASE_URL_ENV,
    DEFAULT_BASE_URL,
    TOKEN_ENV,
    UpsertOutcome,
    _normalise,
)

# writers/contents.py -> importer 包 -> apps/importer
_APP_DIR = Path(__file__).resolve().parent.parent.parent
# 自撰 MDX 正文的「权威源」：committed，版本可控；mdx 子命令从这里读，再镜像到 out/
CONTENT_ROOT = _APP_DIR / "content"

COLLECTION = "contents"
NODE_COLLECTION = "nodes"

# 由 importer 管理的列（status 仅在新建时写入，不纳入 PATCH 差异比对）
MANAGED_FIELDS = ("node", "body_ref", "format", "checksum", "version")

# body_ref 是 varchar(512)；中文按字符计，给一点余量做硬上限
MAX_BODY_CHARS = 512


def checksum(body: str) -> str:
    """正文 sha256（hex），作为 ``checksum`` 字段与差异比对依据。"""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class ContentsError(RuntimeError):
    """contents 写入失败（权限、集合不存在、网络、正文超长等）。"""


class ContentsWriter:
    """最小化的 Directus 写入器（只处理 ``contents`` 集合）。"""

    def __init__(self, base_url: str, token: str, *, timeout: float = 30.0) -> None:
        if not base_url:
            raise ContentsError("缺少 Directus 地址（--base-url 或环境变量 DIRECTUS_URL）")
        if not token:
            raise ContentsError(f"缺少管理员 token（--token 或环境变量 {TOKEN_ENV}）")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    # ---- 生命周期 ----

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ContentsWriter":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @classmethod
    def from_env(cls, *, base_url: str | None = None, token: str | None = None) -> "ContentsWriter":
        return cls(
            base_url or os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL),
            token or os.environ.get(TOKEN_ENV, ""),
        )

    # ---- 对外接口 ----

    def ensure_collection(self) -> None:
        """探测 contents 集合是否可读写；不可用时给出明确提示。"""
        try:
            response = self._client.get(f"/items/{COLLECTION}", params={"limit": 1})
        except httpx.HTTPError as exc:
            raise ContentsError(f"连不上 Directus：{exc}") from exc
        if response.status_code in (401, 403):
            raise ContentsError(
                f"Directus 拒绝访问 contents 集合（HTTP {response.status_code}），请检查 token 权限"
            )
        if response.status_code == 404:
            raise ContentsError(
                "Directus 里还没有 contents 集合：等 01 分支（kuoleroy/directus-collections）"
                " 建表并合并进 main 后再跑 mdx"
            )
        if response.status_code >= 400:
            raise ContentsError(
                f"探测 contents 集合失败：HTTP {response.status_code} {response.text[:200]}"
            )

    def resolve_node_id(self, slug: str) -> int | None:
        """按 ``slug`` 查 ``nodes.id``；找不到返回 ``None``。"""
        response = self._request(
            "GET",
            f"/items/{NODE_COLLECTION}",
            params={
                "filter[slug][_eq]": slug,
                "fields": "id,slug",
                "limit": 1,
            },
        )
        data = response.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, Mapping) and first.get("id") is not None:
                return int(first["id"])  # type: ignore[arg-type]
        return None

    def upsert(self, row: Mapping[str, Any]) -> str:
        """按 ``node`` 幂等写入一条正文，返回 created / updated / unchanged。

        ``row`` 需含 ``node``（整数 id）、``body_ref``（MDX 字符串）、``format``、
        ``checksum``。``version`` 由本方法计算：新建 = 1，正文变化 = 现有 +1。
        """
        node_id = row.get("node")
        if node_id is None:
            raise ContentsError(f"记录缺少 node（slug={row.get('slug')!r}）")
        if not isinstance(row.get("body_ref"), str) or not row["body_ref"].strip():
            raise ContentsError(f"正文 body_ref 为空（slug={row.get('slug')!r}）")
        if len(row["body_ref"]) > MAX_BODY_CHARS:
            raise ContentsError(
                f"正文超长 {len(row['body_ref'])} 字符（上限 {MAX_BODY_CHARS}，"
                f"body_ref 是 varchar(512)）：slug={row.get('slug')!r}"
            )

        existing = self._find_by_node(int(node_id))
        payload = {key: row[key] for key in MANAGED_FIELDS if key in row}

        if existing is None:
            payload = {**payload, "version": 1, "status": "draft"}
            self._create(payload)
            return "created"

        changes = {
            key: value
            for key, value in payload.items()
            if _normalise(existing.get(key)) != _normalise(value)
        }
        if not changes:
            return "unchanged"
        # 仅当正文本身变化时才抬升版本号（checksum 已随正文变化）
        if _normalise(existing.get("checksum")) != _normalise(row.get("checksum")):
            changes["version"] = int(existing.get("version") or 0) + 1
        self._update(existing["id"], changes)
        return "updated"

    def upsert_many(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        dry_run: bool = False,
    ) -> UpsertOutcome:
        """批量 upsert；``dry_run`` 时只统计会新建 / 更新 / 无变化多少条（不落库）。"""
        outcome = UpsertOutcome()
        for row in rows:
            slug = str(row.get("slug") or "")
            try:
                if dry_run:
                    outcome.merge(self._classify(row))
                else:
                    outcome.merge(self.upsert(row))
            except ContentsError as exc:
                outcome.failed[slug] = str(exc)
        return outcome

    # ---- 内部实现 ----

    def _classify(self, row: Mapping[str, Any]) -> str:
        """dry-run 用的只读分类：查现有内容，判断会新建 / 更新 / 无变化。"""
        node_id = row.get("node")
        if node_id is None:
            raise ContentsError(f"记录缺少 node（slug={row.get('slug')!r}）")
        existing = self._find_by_node(int(node_id))
        if existing is None:
            return "created"
        payload = {key: row[key] for key in MANAGED_FIELDS if key in row}
        changes = {
            key: value
            for key, value in payload.items()
            if _normalise(existing.get(key)) != _normalise(value)
        }
        return "updated" if changes else "unchanged"

    def _find_by_node(self, node_id: int) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            f"/items/{COLLECTION}",
            params={
                "filter[node][_eq]": node_id,
                "fields": "*",
                "limit": 1,
            },
        )
        data = response.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, Mapping):
                return dict(first)
        return None

    def _create(self, payload: Mapping[str, Any]) -> None:
        self._request("POST", f"/items/{COLLECTION}", json=payload)

    def _update(self, record_id: Any, changes: Mapping[str, Any]) -> None:
        self._request("PATCH", f"/items/{COLLECTION}/{record_id}", json=changes)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ContentsError(f"{method} {path} 失败：{exc}") from exc
        if response.status_code >= 400:
            raise ContentsError(
                f"{method} {path} 返回 HTTP {response.status_code}：{response.text[:300]}"
            )
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}
