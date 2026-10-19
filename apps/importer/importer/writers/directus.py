"""写入库：走 Directus ``/items/nodes`` REST 做幂等 upsert（步骤 4）。

**为什么选 Directus REST 而不是直连 MySQL**
1. 规范铁律：CRUD / 数据管理归 Directus，FastAPI 只做只读，写入口应当唯一；
2. 权限、审计、字段校验都由 Directus 负责，importer 不必持有数据库凭据；
3. 跨机器复现只依赖一个 URL + 一个管理员 token。

**幂等**：以 ``source_id``（= QID）为业务键先查后写——查到就 PATCH 有差异的字段，
查不到才 POST；字段全一致则跳过。``slug`` 在表上还有 unique 约束，双保险。

**discipline 只在新建时写入**（见 ``CREATE_ONLY_FIELDS``）：自 13.19 起，节点归属的
「大类」由 Directus 后台的 ``categories`` 集合管理（门户按阶段渲染），重跑 push 不该把
后台调整过的归属拉回 taxonomy.yaml 里的旧学科值。其余字段照旧按差异 PATCH。

**状态**：nodes 表由 01 分支建，本模块尚未联调验证（等主控通知后再跑 push）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import httpx

COLLECTION = "nodes"
# 由 importer 管理的列（不碰 id / created_at / updated_at）
MANAGED_FIELDS = (
    "slug",
    "type",
    "title",
    "summary",
    "stage",
    "discipline",
    "tradition",
    "language",
    "status",
    "source_id",
    "source_url",
)

# 仅新建时写入、重跑 push 不纳入 PATCH 差异比对的列。
# discipline（阶段大类）自 13.19 起改由 Directus 后台的 categories 集合管理，
# 数据库才是权威；若这里照 PATCH，重跑 push 会把后台改过的归属拉回 taxonomy 的旧学科值。
CREATE_ONLY_FIELDS = ("discipline",)

DEFAULT_BASE_URL = "http://127.0.0.1:8055"
TOKEN_ENV = "DIRECTUS_TOKEN"
BASE_URL_ENV = "DIRECTUS_URL"


class DirectusError(RuntimeError):
    """Directus 调用失败（权限、集合不存在、网络等）。"""


@dataclass
class UpsertOutcome:
    """一次批量 upsert 的统计。"""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged

    def merge(self, action: str) -> None:
        if action == "created":
            self.created += 1
        elif action == "updated":
            self.updated += 1
        else:
            self.unchanged += 1


class DirectusWriter:
    """最小化的 Directus 写入器（只处理 nodes 集合）。"""

    def __init__(self, base_url: str, token: str, *, timeout: float = 30.0) -> None:
        if not base_url:
            raise DirectusError("缺少 Directus 地址（--base-url 或环境变量 DIRECTUS_URL）")
        if not token:
            raise DirectusError(f"缺少管理员 token（--token 或环境变量 {TOKEN_ENV}）")
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

    def __enter__(self) -> "DirectusWriter":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @classmethod
    def from_env(cls, *, base_url: str | None = None, token: str | None = None) -> "DirectusWriter":
        """从参数或环境变量构造。"""
        return cls(
            base_url or os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL),
            token or os.environ.get(TOKEN_ENV, ""),
        )

    # ---- 对外接口 ----

    def ensure_collection(self) -> None:
        """探测 nodes 集合是否可读写；不可用时给出明确提示。"""
        try:
            response = self._client.get(f"/items/{COLLECTION}", params={"limit": 1})
        except httpx.HTTPError as exc:
            raise DirectusError(f"连不上 Directus：{exc}") from exc
        if response.status_code in (401, 403):
            raise DirectusError(
                f"Directus 拒绝访问 nodes 集合（HTTP {response.status_code}），请检查 token 权限"
            )
        if response.status_code == 404:
            raise DirectusError(
                "Directus 里还没有 nodes 集合：等 01 分支（kuoleroy/directus-collections）"
                " 建表并合并进 main 后再跑 push"
            )
        if response.status_code >= 400:
            raise DirectusError(
                f"探测 nodes 集合失败：HTTP {response.status_code} {response.text[:200]}"
            )

    def upsert(self, row: Mapping[str, Any]) -> str:
        """按 ``source_id`` 幂等写入一条记录，返回 created / updated / unchanged。"""
        source_id = row.get("source_id")
        if not source_id:
            raise DirectusError(f"记录缺少 source_id：{row.get('slug')!r}")

        existing = self._find_by_source_id(str(source_id))
        payload = {key: row[key] for key in MANAGED_FIELDS if key in row}

        if existing is None:
            self._create(payload)
            return "created"

        changes = {
            key: value
            for key, value in payload.items()
            if key not in CREATE_ONLY_FIELDS
            and _normalise(existing.get(key)) != _normalise(value)
        }
        if not changes:
            return "unchanged"
        self._update(existing["id"], changes)
        return "updated"

    def upsert_many(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        dry_run: bool = False,
    ) -> UpsertOutcome:
        """批量 upsert；``dry_run`` 时只统计会新建多少条。"""
        outcome = UpsertOutcome()
        for row in rows:
            slug = str(row.get("slug") or "")
            try:
                if dry_run:
                    existing = self._find_by_source_id(str(row.get("source_id") or ""))
                    outcome.merge("unchanged" if existing else "created")
                else:
                    outcome.merge(self.upsert(row))
            except DirectusError as exc:
                outcome.failed[slug] = str(exc)
        return outcome

    # ---- 内部实现 ----

    def _find_by_source_id(self, source_id: str) -> dict[str, Any] | None:
        if not source_id:
            return None
        response = self._request(
            "GET",
            f"/items/{COLLECTION}",
            params={
                "filter[source_id][_eq]": source_id,
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
            raise DirectusError(f"{method} {path} 失败：{exc}") from exc
        if response.status_code >= 400:
            raise DirectusError(
                f"{method} {path} 返回 HTTP {response.status_code}：{response.text[:300]}"
            )
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}


def _normalise(value: Any) -> Any:
    """比较用归一化：空字符串与 None 视为等价。"""
    if isinstance(value, str) and not value.strip():
        return None
    return value
