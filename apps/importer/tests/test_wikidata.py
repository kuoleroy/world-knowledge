"""SPARQL 组装测试：路径可控、参数正确替换。"""

from __future__ import annotations

import unittest

from importer.config import Filters
from importer.models import Seed
from importer.sources.wikidata import build_query

FILTERS = Filters(
    min_sitelinks=5,
    require_zh_label=True,
    require_zh_sitelink=True,
    allow_en_summary=False,
    exclude_qids={},
)


def _seed(**overrides: object) -> Seed:
    values: dict[str, object] = {
        "qid": "Q200253",
        "discipline": "health_medicine",
        "tradition": "holistic",
        "limit": 4,
    }
    values.update(overrides)
    return Seed(**values)  # type: ignore[arg-type]


class BuildQueryTest(unittest.TestCase):
    def test_no_direct_subclass_path_by_default(self) -> None:
        query = build_query(_seed(), FILTERS, "zh-hans,zh")
        self.assertNotIn("?item wdt:P279 wd:Q200253", query)
        self.assertIn("?item wdt:P31/wdt:P279? wd:Q200253", query)
        self.assertIn("?item wdt:P361/wdt:P279? wd:Q200253", query)
        self.assertIn("VALUES ?item { wd:Q200253 }", query)

    def test_include_subclasses_adds_path(self) -> None:
        query = build_query(_seed(include_subclasses=True), FILTERS, "zh-hans,zh")
        self.assertIn("?item wdt:P279 wd:Q200253", query)

    def test_uses_seed_min_sitelinks_when_set(self) -> None:
        query = build_query(_seed(min_sitelinks=40), FILTERS, "zh-hans,zh")
        self.assertIn("FILTER(?sitelinks >= 40)", query)

    def test_falls_back_to_global_min_sitelinks(self) -> None:
        query = build_query(_seed(), FILTERS, "zh-hans,zh")
        self.assertIn("FILTER(?sitelinks >= 5)", query)

    def test_limit_has_headroom_and_language_list_is_used(self) -> None:
        query = build_query(_seed(limit=4), FILTERS, "zh-hans,zh-cn,zh,en")
        self.assertIn("LIMIT 16", query)
        self.assertIn('bd:serviceParam wikibase:language "zh-hans,zh-cn,zh,en"', query)

    def test_no_unresolved_placeholders(self) -> None:
        query = build_query(_seed(), FILTERS, "zh")
        self.assertNotIn("%(", query)


if __name__ == "__main__":
    unittest.main()
