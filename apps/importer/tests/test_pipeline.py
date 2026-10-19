"""管道测试：断网跑假 Fetcher，验证落盘、幂等、限流取样与传统覆盖。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from importer.config import AppConfig, load_config
from importer.models import RawItem
from importer.net import FetchError
from importer.pipeline import RunOptions, run
from importer.skeleton import find_repo_root, load_skeleton

from tests.support import FakeFetcher, make_item

APP_DIR = Path(__file__).resolve().parent.parent
ITEMS_PER_SEED = 3


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skeleton = load_skeleton(find_repo_root(APP_DIR))
        cls.config: AppConfig = load_config(APP_DIR, cls.skeleton)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.out_dir = Path(self._tmp.name)
        self.fetcher = FakeFetcher(self._build_items())

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ---- 测试数据 ----

    def _build_items(self) -> dict[str, list[RawItem]]:
        """每个种子造 3 条，QID 由种子编号派生，保证唯一且可复现。"""
        plan = self.config.taxonomy.plan("health_medicine")
        mapping: dict[str, list[RawItem]] = {}
        for seed in plan.seeds:
            base = int(seed.qid[1:]) * 10
            mapping[seed.qid] = [
                make_item(
                    qid=f"Q{base + index}",
                    label_zh=f"测试条目{seed.qid}_{index}",
                    desc_zh="示例描述",
                    sitelinks=100,
                    seed=seed,
                )
                for index in range(ITEMS_PER_SEED)
            ]
        return mapping

    def _run(self, *, limit: int = 60) -> "run":
        return run(
            self.config,
            self.fetcher,  # type: ignore[arg-type]
            RunOptions(discipline="health_medicine", limit=limit, with_wikipedia=False, out_dir=self.out_dir),
        )

    # ---- 断言 ----

    def test_outputs_are_written(self) -> None:
        result = self._run()
        self.assertTrue(result.nodes_path.is_file())
        self.assertTrue(result.annotations_path.is_file())
        self.assertTrue(result.summary_path.is_file())
        self.assertGreater(len(result.nodes), 0)

    def test_nodes_rows_only_use_nodes_columns(self) -> None:
        result = self._run()
        rows = [json.loads(line) for line in result.nodes_path.read_text(encoding="utf-8").splitlines()]
        expected = {
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
        }
        for row in rows:
            self.assertEqual(set(row), expected)

    def test_limit_is_respected_and_slugs_unique(self) -> None:
        result = self._run(limit=12)
        slugs = [node.slug for node in result.nodes]
        self.assertEqual(len(slugs), 12)
        self.assertEqual(len(set(slugs)), 12)

    def test_all_traditions_get_seats(self) -> None:
        result = self._run(limit=25)
        self.assertEqual(set(result.by_tradition), set(self.skeleton.traditions))
        for tradition, count in result.by_tradition.items():
            self.assertGreaterEqual(count, 1, f"传统 {tradition} 没有席位")

    def test_all_ids_are_valid_skeleton_values(self) -> None:
        result = self._run()
        for node in result.nodes:
            self.assertIn(node.stage, self.skeleton.stages)
            self.assertIn(node.discipline, self.skeleton.disciplines)
            self.assertIn(node.tradition, self.skeleton.traditions)

    def test_rerun_is_idempotent(self) -> None:
        """同一份输入重复跑，产出逐字节一致（不产生重复节点）。"""
        self._run(limit=20)
        first_nodes = (self.out_dir / "health_medicine" / "nodes.jsonl").read_bytes()
        first_annotations = (self.out_dir / "health_medicine" / "annotations.jsonl").read_bytes()

        self._run(limit=20)
        second_nodes = (self.out_dir / "health_medicine" / "nodes.jsonl").read_bytes()
        second_annotations = (self.out_dir / "health_medicine" / "annotations.jsonl").read_bytes()

        self.assertEqual(first_nodes, second_nodes)
        self.assertEqual(first_annotations, second_annotations)

    def test_item_without_zh_wikipedia_is_skipped(self) -> None:
        seed = self.config.taxonomy.plan("health_medicine").seeds[0]
        self.fetcher = FakeFetcher(
            {
                seed.qid: [
                    make_item(qid="Q700001", label_zh="有条目", seed=seed),
                    make_item(qid="Q700002", label_zh="没条目", zhwiki=False, seed=seed),
                ]
            }
        )
        result = self._run(limit=10)
        source_ids = {node.source_id for node in result.nodes}
        self.assertIn("Q700001", source_ids)
        self.assertNotIn("Q700002", source_ids)
        self.assertGreaterEqual(result.skipped.get("no_zh_sitelink", 0), 1)

    def test_excluded_qid_is_skipped(self) -> None:
        excluded = next(iter(self.config.taxonomy.filters.exclude_qids))
        seed = self.config.taxonomy.plan("health_medicine").seeds[0]
        self.fetcher = FakeFetcher(
            {seed.qid: [make_item(qid=excluded, label_zh="黑名单条目", seed=seed)]}
        )
        result = self._run(limit=10)
        self.assertNotIn(excluded, {node.source_id for node in result.nodes})
        self.assertGreaterEqual(result.skipped.get("excluded_by_config", 0), 1)

    def test_summary_file_matches_nodes(self) -> None:
        result = self._run(limit=15)
        summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["total"], len(result.nodes))
        self.assertEqual(summary["discipline"], "health_medicine")

    def test_seed_fetch_failure_does_not_abort_run(self) -> None:
        """单个种子抓取失败只记账，不该拖垮整条导入线。"""
        items = self._build_items()
        failing_qid = self.config.taxonomy.plan("health_medicine").seeds[0].qid

        class FlakyFetcher(FakeFetcher):
            def post_json(self, url, *, data=None, params=None):  # type: ignore[override]
                query = str((data or {}).get("query") or "")
                if failing_qid in query:
                    raise FetchError("模拟网络失败")
                return super().post_json(url, data=data, params=params)

        self.fetcher = FlakyFetcher(items)
        result = self._run(limit=20)
        self.assertEqual(result.skipped.get("seed_failed"), 1)
        self.assertEqual(len(result.warnings), 1)
        self.assertGreater(len(result.nodes), 0)


if __name__ == "__main__":
    unittest.main()
