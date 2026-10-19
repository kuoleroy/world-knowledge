"""学科接口：读取骨架 JSON。"""

from fastapi import APIRouter, HTTPException

from app.schemas.common import success_response
from app.schemas.skeleton import DisciplineOut
from app.skeleton.loader import get_discipline, load_disciplines

router = APIRouter(prefix="/disciplines", tags=["disciplines"])


@router.get("")
def list_disciplines() -> dict:
    """获取 12 个学科大类。"""
    disciplines = [
        DisciplineOut.model_validate(d).model_dump(by_alias=True) for d in load_disciplines()
    ]
    return success_response(disciplines, {"total": len(disciplines)})


@router.get("/{discipline_id}")
def get_discipline_detail(discipline_id: str) -> dict:
    """按 id 获取单个学科。"""
    discipline = get_discipline(discipline_id)
    if discipline is None:
        raise HTTPException(status_code=404, detail=f"学科不存在: {discipline_id}")
    return success_response(DisciplineOut.model_validate(discipline).model_dump(by_alias=True))
