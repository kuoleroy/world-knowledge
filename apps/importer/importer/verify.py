"""落库自检（只读）：条数 / 重复 / 空字段 / 分布 / 内容指纹。

走 Directus 的 public 只读权限（01 已给 `public` 配 `nodes` 读权限），因此**无需 token**
就能核对「门户能看到什么」——与门户的实际读路径一致。

指纹是 60 行管理字段的 sha256（按 slug 排序、字段排序、UTF-8），用于验证复跑幂等：
第二次 push 之后指纹不变，说明既没插重复行、也没把字段改坏。
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import httpx

from .writers.directus import MANAGED_FIELDS

COLLECTION = "nodes"
# 导入必须落全的字段（summary 允许为空：上游没有中文描述）
REQUIRED_FIELDS = ("title", "stage", "discipline", "tradition", "source_id", "source_url")


@dataclass
class VerifyReport:
    """一次自检的结果。"""

    discipline: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    duplicate_slugs: list[str] = field(default_factory=list)
    duplicate_source_ids: list[str] = field(default_factory=list)
    missing: dict[str, list[str]] = field(default_factory=dict)
    missing_summary: int = 0
    by_stage: dict[str, int] = field(default_factory=dict)
    by_tradition: dict[str, int] = field(default_factory=dict)
    fingerprint: str = ""

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def ok(self) -> bool:
        return not self.duplicate_slugs and not self.duplicate_source_ids and not any(self.missing.values())


def summarize(discipline: str, rows: Iterable[Mapping[str, Any]]) -> VerifyReport:
    """对读回的行做一致性检查（纯函数，方便单测）。"""
    items = [dict(row) for row in rows]
    slugs = [str(row.get("slug") or "") for row in items]
    source_ids = [str(row.get("source_id") or "") for row in items]

    report = VerifyReport(
        discipline=discipline,
        rows=items,
        duplicate_slugs=sorted(key for key, count in Counter(slugs).items() if count > 1),
        duplicate_source_ids=sorted(key for key, count in Counter(source_ids).items() if count > 1),
        missing={
            name: [str(row.get("slug") or "?") for row in items if not row.get(name)]
            for name in REQUIRED_FIELDS
        },
        missing_summary=sum(1 for row in items if not row.get("summary")),
        by_stage=dict(sorted(Counter(str(row.get("stage") or "") for row in items).items())),
        by_tradition=dict(sorted(Counter(str(row.get("tradition") or "") for row in items).items())),
    )
    report.fingerprint = fingerprint(items)
    return report


def fingerprint(rows: Iterable[Mapping[str, Any]]) -> str:
    """管理字段的内容指纹；行按 slug 排序，与读回顺序无关。"""
    payload = [
        {key: row.get(key) for key in MANAGED_FIELDS}
        for row in sorted(rows, key=lambda row: str(row.get("slug") or ""))
    ]
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_rows(
    client: httpx.Client,
    discipline: str,
    *,
    token: str | None = None,
) -> list[dict[str, Any]]:
    """按 discipline 读回全部 nodes（不分页）。"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = client.get(
        f"/items/{COLLECTION}",
        params={
            "filter[discipline][_eq]": discipline,
            "limit": -1,
            "fields": "*",
            "sort": "slug",
        },
        headers=headers,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"读取 /items/{COLLECTION} 失败：HTTP {response.status_code} {response.text[:200]}"
        )
    data = response.json().get("data")
    return [dict(row) for row in data or [] if isinstance(row, Mapping)]


def run(base_url: str, discipline: str, *, token: str | None = None, timeout: float = 30.0) -> VerifyReport:
    """连 Directus 读回并自检。"""
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        rows = fetch_rows(client, discipline, token=token)
    return summarize(discipline, rows)
