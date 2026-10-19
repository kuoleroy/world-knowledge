"""落库自检的纯函数测试（不联网）。"""

from __future__ import annotations

import unittest

from importer.verify import fingerprint, summarize


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": 1,
        "slug": "wd-Q11190",
        "type": "concept",
        "title": "医学",
        "summary": "診斷，治療和預防疾病的研究領域",
        "stage": "learning",
        "discipline": "health_medicine",
        "tradition": "empirical",
        "language": "zh",
        "status": "draft",
        "source_id": "Q11190",
        "source_url": "https://zh.wikipedia.org/wiki/医学",
    }
    row.update(overrides)
    return row


class SummarizeTest(unittest.TestCase):
    def test_clean_rows_pass(self) -> None:
        report = summarize("health_medicine", [_row(slug="wd-Q1", source_id="Q1"), _row(slug="wd-Q2", source_id="Q2")])
        self.assertTrue(report.ok)
        self.assertEqual(report.total, 2)
        self.assertEqual(report.duplicate_slugs, [])
        self.assertEqual(report.duplicate_source_ids, [])
        self.assertEqual(report.by_stage, {"learning": 2})
        self.assertEqual(report.by_tradition, {"empirical": 2})
        self.assertEqual(report.missing_summary, 0)

    def test_duplicate_slug_is_reported(self) -> None:
        report = summarize(
            "health_medicine",
            [_row(slug="wd-Q1", source_id="Q1"), _row(slug="wd-Q1", source_id="Q2")],
        )
        self.assertFalse(report.ok)
        self.assertEqual(report.duplicate_slugs, ["wd-Q1"])

    def test_duplicate_source_id_is_reported(self) -> None:
        report = summarize(
            "health_medicine",
            [_row(slug="wd-Q1", source_id="Q1"), _row(slug="wd-Q2", source_id="Q1")],
        )
        self.assertFalse(report.ok)
        self.assertEqual(report.duplicate_source_ids, ["Q1"])

    def test_missing_required_field_is_reported(self) -> None:
        report = summarize("health_medicine", [_row(source_url=None)])
        self.assertFalse(report.ok)
        self.assertEqual(report.missing["source_url"], ["wd-Q11190"])

    def test_missing_summary_does_not_fail(self) -> None:
        report = summarize("health_medicine", [_row(summary=None)])
        self.assertTrue(report.ok)
        self.assertEqual(report.missing_summary, 1)

    def test_fingerprint_ignores_row_order(self) -> None:
        rows = [_row(slug="wd-Q1", source_id="Q1"), _row(slug="wd-Q2", source_id="Q2")]
        self.assertEqual(fingerprint(rows), fingerprint(list(reversed(rows))))

    def test_fingerprint_changes_when_content_changes(self) -> None:
        rows = [_row(slug="wd-Q1", source_id="Q1")]
        changed = [_row(slug="wd-Q1", source_id="Q1", title="医学（改写）")]
        self.assertNotEqual(fingerprint(rows), fingerprint(changed))


if __name__ == "__main__":
    unittest.main()
