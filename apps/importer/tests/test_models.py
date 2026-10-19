"""models 的单元测试：slug 规则、标题/摘要回退、节点字段映射。"""

from __future__ import annotations

import unittest

from importer.models import NodeDraft, RawItem, Seed, wikidata_slug


def _seed(**overrides: object) -> Seed:
    values: dict[str, object] = {
        "qid": "Q11190",
        "discipline": "health_medicine",
        "tradition": "empirical",
    }
    values.update(overrides)
    return Seed(**values)  # type: ignore[arg-type]


def _item(**overrides: object) -> RawItem:
    values: dict[str, object] = {
        "qid": "Q200253",
        "label_zh": "中医学",
        "label_en": "traditional Chinese medicine",
        "desc_zh": "中国传统医学",
        "desc_en": "traditional medicine of China",
        "zhwiki_url": "https://zh.wikipedia.org/wiki/中医学",
        "enwiki_url": "https://en.wikipedia.org/wiki/Traditional_Chinese_medicine",
        "sitelinks": 60,
        "primary_seed": _seed(),
        "seed_qids": {"Q200253"},
    }
    values.update(overrides)
    return RawItem(**values)  # type: ignore[arg-type]


class SlugTest(unittest.TestCase):
    def test_wikidata_slug_keeps_qid_case(self) -> None:
        self.assertEqual(wikidata_slug("Q12345"), "wd-Q12345")
        self.assertEqual(wikidata_slug("Q1"), "wd-Q1")

    def test_rejects_malformed_qid(self) -> None:
        for bad in ["12345", "Q0", "Qabc", "q123", "wd-Q1", ""]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wikidata_slug(bad)


class RawItemTest(unittest.TestCase):
    def test_title_prefers_chinese(self) -> None:
        self.assertEqual(_item().title, "中医学")

    def test_title_falls_back_to_english(self) -> None:
        self.assertEqual(_item(label_zh=None).title, "traditional Chinese medicine")

    def test_title_is_none_without_labels(self) -> None:
        self.assertIsNone(_item(label_zh=None, label_en=None).title)

    def test_summary_only_uses_chinese_description(self) -> None:
        self.assertEqual(_item().summary, "中国传统医学")
        self.assertIsNone(_item(desc_zh=None).summary)

    def test_source_url_prefers_zhwiki(self) -> None:
        item = _item()
        self.assertEqual(item.wikipedia_url, item.zhwiki_url)
        self.assertEqual(_item(zhwiki_url=None).wikipedia_url, _item().enwiki_url)

    def test_corpus_merges_labels_and_descriptions(self) -> None:
        corpus = _item().corpus
        self.assertIn("中医学", corpus)
        self.assertIn("traditional chinese medicine", corpus)
        self.assertIn("中国传统医学", corpus)


class NodeDraftTest(unittest.TestCase):
    def test_to_row_matches_nodes_columns(self) -> None:
        draft = NodeDraft(
            slug="wd-Q200253",
            type="concept",
            title="中医学",
            summary="中国传统医学",
            stage="learning",
            discipline="health_medicine",
            tradition="holistic",
            language="zh",
            status="draft",
            source_id="Q200253",
            source_url="https://zh.wikipedia.org/wiki/中医学",
        )
        row = draft.to_row()
        self.assertEqual(
            set(row),
            {
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
            },
        )
        self.assertEqual(row["source_id"], "Q200253")


if __name__ == "__main__":
    unittest.main()
