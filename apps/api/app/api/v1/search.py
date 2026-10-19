"""搜索接口：占位（搜索索引待接入 Meilisearch）。"""

from fastapi import APIRouter

from app.schemas.common import success_response

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str = "") -> dict:
    """全文搜索占位：暂返回空结果。"""
    return success_response(
        [],
        {"query": q, "total": 0, "note": "搜索索引待接入 Meilisearch"},
    )
