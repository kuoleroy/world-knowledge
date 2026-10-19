"""Wikidata 抓取：按种子条目查子树，产出候选条目。

只要结构化事实（QID / 中英文标签 / 中文描述 / 维基条目链接 / 站点链接数），
不抓维基正文——正文在 :mod:`importer.sources.wikipedia` 单独取，且只作改寫素材。

查询用 ``wdt:P31/wdt:P279?``（实例及其一层上位类）、``wdt:P279``（直接子类）、
``wdt:P361/wdt:P279?``（组成部分）四条路径取并集，深度受控，避免像 ``疾病`` 这种
巨型子树把查询服务打超时。
"""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import unquote

from ..config import Filters, SourcesConfig
from ..models import RawItem, Seed
from ..net import Fetcher

SPARQL_TEMPLATE = """
SELECT DISTINCT ?item ?itemLabel ?itemDescription ?zhwiki ?enwiki ?sitelinks WHERE {
  %(paths)s
  ?item wikibase:sitelinks ?sitelinks .
  FILTER(?sitelinks >= %(min_sitelinks)d)
  OPTIONAL { ?zhwiki schema:about ?item ; schema:isPartOf <https://zh.wikipedia.org/> . }
  OPTIONAL { ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }
  FILTER(BOUND(?zhwiki) || BOUND(?enwiki))
  SERVICE wikibase:label { bd:serviceParam wikibase:language "%(label_languages)s". }
}
ORDER BY DESC(?sitelinks)
LIMIT %(limit)d
""".strip()

# 四条取数路径：实例（含一层上位类）、组成部分、种子自身，可选「直接子类」
PATH_INSTANCE = "{ ?item wdt:P31/wdt:P279? wd:%(qid)s . }"
PATH_PART_OF = "{ ?item wdt:P361/wdt:P279? wd:%(qid)s . }"
PATH_SELF = "{ VALUES ?item { wd:%(qid)s } }"
PATH_SUBCLASS = "{ ?item wdt:P279 wd:%(qid)s . }"


def build_query(seed: Seed, filters: Filters, label_languages: str) -> str:
    """组装单个种子的 SPARQL 查询。

    请求行数取 ``limit * 4`` 作为余量：后面还要按中文标签/中文条目再筛一遍。
    是否展开直接子类由 ``seed.include_subclasses`` 控制（默认不展开，见 ``Seed`` 注释）。
    """
    min_sitelinks = seed.min_sitelinks if seed.min_sitelinks is not None else filters.min_sitelinks
    paths = [PATH_INSTANCE, PATH_PART_OF, PATH_SELF]
    if seed.include_subclasses:
        paths.insert(1, PATH_SUBCLASS)
    return SPARQL_TEMPLATE % {
        "paths": " UNION ".join(paths) % {"qid": seed.qid},
        "min_sitelinks": min_sitelinks,
        "label_languages": label_languages,
        "limit": max(seed.limit * 4, 10),
    }


def fetch_seed(
    fetcher: Fetcher,
    sources: SourcesConfig,
    seed: Seed,
    filters: Filters,
) -> list[RawItem]:
    """抓一个种子的子树原始结果。

    这里只做 SPARQL 层的粗筛（站点链接数下限）和解析，质量过滤与每种子上限统一放在
    :mod:`importer.pipeline`——这样跳过原因能汇总进 ``summary.json``，不会悄悄丢条目。
    """
    query = build_query(seed, filters, sources.label_languages)
    payload = fetcher.post_json(
        sources.sparql_endpoint,
        data={"query": query, "format": "json"},
    )

    items: list[RawItem] = []
    seen: set[str] = set()
    for binding in _bindings(payload):
        item = _to_raw_item(binding, seed)
        if item is None or item.qid in seen:
            continue
        seen.add(item.qid)
        items.append(item)
    return items


def _bindings(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    results = payload.get("results")
    if not isinstance(results, Mapping):
        return []
    rows = results.get("bindings")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _to_raw_item(binding: Mapping[str, Any], seed: Seed) -> RawItem | None:
    qid = _qid(binding)
    if qid is None:
        return None
    label_zh, label_en = _label(binding, "itemLabel")
    desc_zh, desc_en = _label(binding, "itemDescription")
    item = RawItem(
        qid=qid,
        label_zh=label_zh,
        label_en=label_en,
        desc_zh=desc_zh,
        desc_en=desc_en,
        zhwiki_url=_url(binding, "zhwiki"),
        enwiki_url=_url(binding, "enwiki"),
        sitelinks=_sitelinks(binding),
        primary_seed=seed,
        seed_qids={seed.qid},
    )
    return item if item.title else None


def _value(binding: Mapping[str, Any], key: str) -> str | None:
    node = binding.get(key)
    if not isinstance(node, Mapping):
        return None
    value = node.get("value")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _qid(binding: Mapping[str, Any]) -> str | None:
    url = _value(binding, "item")
    if not url:
        return None
    qid = unquote(url.rsplit("/", 1)[-1])
    return qid if qid.startswith("Q") and qid[1:].isdigit() else None


def _label(binding: Mapping[str, Any], key: str) -> tuple[str | None, str | None]:
    """按 ``xml:lang`` 把标签/描述分流到中文、英文。"""
    node = binding.get(key)
    if not isinstance(node, Mapping):
        return (None, None)
    value = node.get("value")
    if not isinstance(value, str) or not value.strip():
        return (None, None)
    lang = str(node.get("xml:lang") or "")
    text = value.strip()
    if lang.startswith("zh"):
        return (text, None)
    if lang.startswith("en"):
        return (None, text)
    return (None, None)


def _url(binding: Mapping[str, Any], key: str) -> str | None:
    return _value(binding, key)


def _sitelinks(binding: Mapping[str, Any]) -> int:
    raw = _value(binding, "sitelinks")
    if not raw:
        return 0
    try:
        return int(float(raw))
    except ValueError:
        return 0
