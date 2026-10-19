"""阶段接口：读取骨架 JSON。"""

from fastapi import APIRouter, HTTPException

from app.schemas.common import success_response
from app.schemas.skeleton import StageOut
from app.skeleton.loader import get_stage, load_stages

router = APIRouter(prefix="/stages", tags=["stages"])


@router.get("")
def list_stages() -> dict:
    """获取 4 个教育阶段。"""
    stages = [StageOut.model_validate(s).model_dump(by_alias=True) for s in load_stages()]
    return success_response(stages, {"total": len(stages)})


@router.get("/{stage_code}")
def get_stage_detail(stage_code: str) -> dict:
    """按 id 获取单个阶段。"""
    stage = get_stage(stage_code)
    if stage is None:
        raise HTTPException(status_code=404, detail=f"阶段不存在: {stage_code}")
    return success_response(StageOut.model_validate(stage).model_dump(by_alias=True))
