"""只读加载骨架定义（4 阶段 / 12 学科 / 5 传统）。

骨架 JSON 是冻结契约（``apps/api/app/data/skeleton/*.json``），本模块**只读不写**，
用于校验配置文件里出现的 id，避免自造 id 产出脏数据。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SKELETON_RELATIVE = Path("apps/api/app/data/skeleton")


class SkeletonError(RuntimeError):
    """骨架文件缺失或格式不符。"""


@dataclass(frozen=True)
class Skeleton:
    """骨架定义快照。"""

    stages: tuple[str, ...]
    disciplines: dict[str, str]
    traditions: tuple[str, ...]
    root: Path

    def has_stage(self, value: str) -> bool:
        return value in self.stages

    def has_discipline(self, value: str) -> bool:
        return value in self.disciplines

    def has_tradition(self, value: str) -> bool:
        return value in self.traditions


def find_repo_root(start: Path) -> Path:
    """从 ``start`` 向上找仓库根（含 ``.git`` 或主文档的目录）。"""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (
            candidate / "世界知识门户项目知识文档.md"
        ).exists():
            return candidate
    raise SkeletonError(f"找不到仓库根目录（从 {start} 向上查找 .git 失败）")


def _load_json(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SkeletonError(f"骨架文件缺失：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - 骨架文件损坏才会触发
        raise SkeletonError(f"骨架文件不是合法 JSON：{path}（{exc}）") from exc
    if not isinstance(payload, list):
        raise SkeletonError(f"骨架文件顶层应为数组：{path}")
    return payload


def load_skeleton(repo_root: Path) -> Skeleton:
    """读取三份骨架 JSON，返回可校验的骨架快照。"""
    skeleton_dir = repo_root / SKELETON_RELATIVE
    stages = _load_json(skeleton_dir / "stages.json")
    disciplines = _load_json(skeleton_dir / "disciplines.json")
    traditions = _load_json(skeleton_dir / "traditions.json")

    return Skeleton(
        stages=tuple(str(entry["id"]) for entry in stages),
        disciplines={
            str(entry["id"]): str(entry.get("nameZh") or entry["id"])
            for entry in disciplines
        },
        traditions=tuple(str(entry["id"]) for entry in traditions),
        root=repo_root,
    )
