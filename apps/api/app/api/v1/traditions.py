"""知识传统接口：读取骨架 JSON。"""

from fastapi import APIRouter, HTTPException

from app.schemas.common import success_response
from app.schemas.skeleton import TraditionOut
from app.skeleton.loader import get_tradition, load_traditions

router = APIRouter(prefix="/traditions", tags=["traditions"])


@router.get("")
def list_traditions() -> dict:
    """获取 5 个知识传统标签。"""
    traditions = [
        TraditionOut.model_validate(t).model_dump(by_alias=True) for t in load_traditions()
    ]
    return success_response(traditions, {"total": len(traditions)})


@router.get("/{tradition_code}")
def get_tradition_detail(tradition_code: str) -> dict:
    """按 id 获取单个知识传统。"""
    tradition = get_tradition(tradition_code)
    if tradition is None:
        raise HTTPException(status_code=404, detail=f"知识传统不存在: {tradition_code}")
    return success_response(TraditionOut.model_validate(tradition).model_dump(by_alias=True))
