"""骨架数据加载器：读取 app/data/skeleton 下的 JSON 文件。"""

import json
from functools import lru_cache
from pathlib import Path

# 骨架数据目录：app/data/skeleton
SKELETON_DIR = Path(__file__).resolve().parent.parent / "data" / "skeleton"


def _load_json(filename: str) -> list[dict]:
    """读取并解析指定 JSON 文件。"""
    path = SKELETON_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_stages() -> list[dict]:
    """加载 4 个教育阶段。"""
    return _load_json("stages.json")


@lru_cache
def load_disciplines() -> list[dict]:
    """加载 12 个学科大类。"""
    return _load_json("disciplines.json")


@lru_cache
def load_traditions() -> list[dict]:
    """加载 5 个知识传统标签。"""
    return _load_json("traditions.json")


def get_stage(stage_id: str) -> dict | None:
    """按 id 查找单个阶段。"""
    return next((s for s in load_stages() if s["id"] == stage_id), None)


def get_discipline(discipline_id: str) -> dict | None:
    """按 id 查找单个学科。"""
    return next((d for d in load_disciplines() if d["id"] == discipline_id), None)


def get_tradition(tradition_id: str) -> dict | None:
    """按 id 查找单个知识传统。"""
    return next((t for t in load_traditions() if t["id"] == tradition_id), None)
