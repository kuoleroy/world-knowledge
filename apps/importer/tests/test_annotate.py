"""标注规则测试：规则优先、种子回退、人工钉死阶段。"""

from __future__ import annotations

import unittest
from pathlib import Path

from importer.annotate import annotate, build_draft
from importer.config import AppConfig, Taxonomy, load_config
from importer.models import RawItem, Seed
from importer.skeleton import find_repo_root, load_skeleton

from tests.support import make_item

APP_DIR = Path(__file__).resolve().parent.parent


class AnnotateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skeleton = load_skeleton(find_repo_root(APP_DIR))
        cls.config: AppConfig = load_config(APP_DIR, cls.skeleton)
        cls.taxonomy: Taxonomy = cls.config.taxonomy
        plan = cls.taxonomy.plan("health_medicine")
        cls.empirical_seed = next(seed for seed in plan.seeds if seed.qid == "Q11190")
        cls.no_stage_seed = next(seed for seed in plan.seeds if seed.stage is None)

    def _item(
        self,
        seed: Seed,
        *,
        label: str,
        desc: str | None = "示例描述",
        qid: str = "Q900001",
        **kwargs: object,
    ) -> RawItem:
        return make_item(qid=qid, label_zh=label, desc_zh=desc, seed=seed, **kwargs)

    def test_keyword_rule_overrides_seed_tradition(self) -> None:
        item = self._item(self.empirical_seed, label="中医学", desc="中国传统医学")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.tradition, "holistic")
        self.assertTrue(any("关键词" in reason for reason in annotation.reasons))

    def test_falls_back_to_seed_tradition(self) -> None:
        item = self._item(self.empirical_seed, label="听诊器", desc="医生用于听诊的器具")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.tradition, "empirical")
        self.assertTrue(any("继承种子" in reason for reason in annotation.reasons))

    def test_holistic_rule_beats_experiential_when_both_match(self) -> None:
        item = self._item(self.empirical_seed, label="中医助产", desc="传统接生方法")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.tradition, "holistic")

    def test_seed_stage_pin_applies_to_seed_item_itself(self) -> None:
        item = self._item(
            self.empirical_seed,
            qid=self.empirical_seed.qid,
            label="临床试验",
            desc="医学研究",
        )
        annotation = annotate(item, self.taxonomy)
        # Q11190 人工钉了 stage=learning，即使文本命中 research 也应保持 learning
        self.assertEqual(annotation.stage, "learning")
        self.assertTrue(any("人工指定" in reason for reason in annotation.reasons))

    def test_seed_stage_pin_does_not_leak_to_descendants(self) -> None:
        """种子的 stage 只钉种子条目本身，子树条目仍走关键词规则。"""
        item = self._item(self.empirical_seed, qid="Q900777", label="临床试验", desc="医学研究")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.stage, "research")

    def test_stage_rule_matches_practice(self) -> None:
        item = self._item(self.no_stage_seed, label="外科手术", desc="通过手术治疗疾病")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.stage, "change")

    def test_stage_defaults_when_nothing_matches(self) -> None:
        item = self._item(self.no_stage_seed, label="听诊器", desc="医生用于听诊的器具")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.stage, self.taxonomy.defaults.stage)

    def test_discipline_comes_from_seed(self) -> None:
        item = self._item(self.empirical_seed, label="听诊器")
        annotation = annotate(item, self.taxonomy)
        self.assertEqual(annotation.discipline, "health_medicine")


class BuildDraftTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skeleton = load_skeleton(find_repo_root(APP_DIR))
        cls.config = load_config(APP_DIR, cls.skeleton)
        cls.taxonomy = cls.config.taxonomy
        cls.seed = cls.taxonomy.plan("health_medicine").seeds[0]

    def test_draft_fields(self) -> None:
        item = make_item(qid="Q200253", label_zh="中医学", desc_zh="中国传统医学", seed=self.seed)
        draft = build_draft(item, annotate(item, self.taxonomy), self.taxonomy)
        self.assertEqual(draft.slug, "wd-Q200253")
        self.assertEqual(draft.source_id, "Q200253")
        self.assertEqual(draft.status, "draft")
        self.assertEqual(draft.language, "zh")
        self.assertEqual(draft.tradition, "holistic")
        self.assertEqual(draft.source_url, item.zhwiki_url)

    def test_english_summary_not_used_by_default(self) -> None:
        item = make_item(
            qid="Q900002",
            label_zh="测试条目",
            desc_zh=None,
            desc_en="an english description",
            seed=self.seed,
        )
        draft = build_draft(item, annotate(item, self.taxonomy), self.taxonomy)
        self.assertIsNone(draft.summary)


if __name__ == "__main__":
    unittest.main()
