"""图谱接口：占位（多跳遍历待接入 Neo4j，前期用 MySQL 存边）。"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def get_graph(focus: str | None = None, depth: int = 1) -> dict:
    """图谱遍历占位：返回基本结构体。"""
    return success_response(
        {"nodes": [], "edges": []},
        {"focus": focus, "depth": depth, "total": 0, "note": "图谱遍历待接入 Neo4j"},
    )
