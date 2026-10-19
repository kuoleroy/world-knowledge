"""配置与骨架校验测试：id 一律来自骨架 JSON，配置写错要当场失败。"""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from importer.config import ConfigError, load_config, validate_taxonomy
from importer.skeleton import find_repo_root, load_skeleton

APP_DIR = Path(__file__).resolve().parent.parent


class RealConfigTest(unittest.TestCase):
    """用仓库里的真实配置跑一遍，确保它与骨架定义同步。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.skeleton = load_skeleton(find_repo_root(APP_DIR))
        cls.config = load_config(APP_DIR, cls.skeleton)

    def test_skeleton_has_expected_shape(self) -> None:
        self.assertEqual(len(self.skeleton.stages), 4)
        self.assertEqual(len(self.skeleton.disciplines), 12)
        self.assertEqual(len(self.skeleton.traditions), 5)

    def test_all_ids_come_from_skeleton(self) -> None:
        taxonomy = self.config.taxonomy
        for plan in taxonomy.plans.values():
            for seed in plan.seeds:
                self.assertIn(seed.tradition, self.skeleton.traditions)
                if seed.stage is not None:
                    self.assertIn(seed.stage, self.skeleton.stages)
        for rule in taxonomy.stage_rules:
            self.assertIn(rule.target, self.skeleton.stages)
        for rule in taxonomy.tradition_rules:
            self.assertIn(rule.target, self.skeleton.traditions)

    def test_health_medicine_plan_covers_all_traditions(self) -> None:
        plan = self.config.taxonomy.plan("health_medicine")
        traditions = {seed.tradition for seed in plan.seeds}
        self.assertEqual(traditions, set(self.skeleton.traditions))

    def test_unknown_discipline_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            self.config.taxonomy.plan("not_a_discipline")


class ValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skeleton = load_skeleton(find_repo_root(APP_DIR))
        cls.taxonomy = load_config(APP_DIR, cls.skeleton).taxonomy

    def _replace_plan(self, discipline: str, seeds: tuple) -> object:
        plan = replace(self.taxonomy.plans[discipline], seeds=seeds)
        return replace(self.taxonomy, plans={**self.taxonomy.plans, discipline: plan})

    def test_rejects_invented_tradition(self) -> None:
        plan = self.taxonomy.plan("health_medicine")
        bad_seed = replace(plan.seeds[0], tradition="invented")
        with self.assertRaises(ConfigError):
            validate_taxonomy(self._replace_plan("health_medicine", (bad_seed,)), self.skeleton)

    def test_rejects_invented_stage(self) -> None:
        plan = self.taxonomy.plan("health_medicine")
        bad_seed = replace(plan.seeds[0], stage="invented")
        with self.assertRaises(ConfigError):
            validate_taxonomy(self._replace_plan("health_medicine", (bad_seed,)), self.skeleton)

    def test_rejects_duplicate_seed(self) -> None:
        plan = self.taxonomy.plan("health_medicine")
        with self.assertRaises(ConfigError):
            validate_taxonomy(
                self._replace_plan("health_medicine", (plan.seeds[0], plan.seeds[0])),
                self.skeleton,
            )

    def test_rejects_discipline_mismatch(self) -> None:
        plan = self.taxonomy.plan("health_medicine")
        bad_seed = replace(plan.seeds[0], discipline="math_natural_sciences")
        with self.assertRaises(ConfigError):
            validate_taxonomy(self._replace_plan("health_medicine", (bad_seed,)), self.skeleton)


if __name__ == "__main__":
    unittest.main()
