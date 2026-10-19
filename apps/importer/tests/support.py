"""测试辅助：离线的假 Fetcher 与条目工厂（不发任何网络请求）。"""

from __future__ import annotations

import re
from typing import Any, Mapping

from importer.models import RawItem, Seed

SEED_PATTERN = re.compile(r"wd:(Q\d+)")


def make_item(
    *,
    qid: str,
    label_zh: str | None,
    label_en: str | None = None,
    desc_zh: str | None = "测试描述",
    desc_en: str | None = None,
    sitelinks: int = 100,
    zhwiki: bool = True,
    seed: Seed,
) -> RawItem:
    """构造一条原始条目。"""
    return RawItem(
        qid=qid,
        label_zh=label_zh,
        label_en=label_en,
        desc_zh=desc_zh,
        desc_en=desc_en,
        zhwiki_url=f"https://zh.wikipedia.org/wiki/{label_zh}" if zhwiki and label_zh else None,
        enwiki_url=f"https://en.wikipedia.org/wiki/{label_en}" if label_en else None,
        sitelinks=sitelinks,
        primary_seed=seed,
        seed_qids={seed.qid},
    )


class FakeFetcher:
    """按 SPARQL 查询里的种子 QID 返回预置结果。"""

    def __init__(self, items_by_seed: Mapping[str, list[RawItem]]) -> None:
        self._items_by_seed = {key: list(value) for key, value in items_by_seed.items()}
        self.queries: list[str] = []

    def post_json(
        self,
        url: str,
        *,
        data: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = str((data or {}).get("query") or "")
        self.queries.append(query)
        match = SEED_PATTERN.search(query)
        qid = match.group(1) if match else ""
        bindings = [_to_binding(item) for item in self._items_by_seed.get(qid, [])]
        return {"head": {"vars": []}, "results": {"bindings": bindings}}

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        ignore_status: tuple[int, ...] = (),
    ) -> dict[str, Any] | None:
        return None

    def close(self) -> None:
        return None

    def __enter__(self) -> "FakeFetcher":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _to_binding(item: RawItem) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{item.qid}"},
        "sitelinks": {"type": "literal", "value": str(item.sitelinks)},
    }
    if item.label_zh:
        binding["itemLabel"] = {"type": "literal", "xml:lang": "zh-hans", "value": item.label_zh}
    elif item.label_en:
        binding["itemLabel"] = {"type": "literal", "xml:lang": "en", "value": item.label_en}
    if item.desc_zh:
        binding["itemDescription"] = {"type": "literal", "xml:lang": "zh", "value": item.desc_zh}
    elif item.desc_en:
        binding["itemDescription"] = {"type": "literal", "xml:lang": "en", "value": item.desc_en}
    if item.zhwiki_url:
        binding["zhwiki"] = {"type": "uri", "value": item.zhwiki_url}
    if item.enwiki_url:
        binding["enwiki"] = {"type": "uri", "value": item.enwiki_url}
    return binding
