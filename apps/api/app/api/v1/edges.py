"""关系边接口：只读（走 MySQL；增删改由 Directus 负责）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from app.db.session import get_db
from app.models.edge import Edge
from app.schemas.common import success_response
from app.schemas.edge import EdgeOut

router = APIRouter(prefix="/edges", tags=["edges"])


@router.get("")
def list_edges(
    source: int | None = None,
    target: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """边列表，可按 source / target 节点 id 过滤（只读）。"""
    try:
        stmt = select(Edge)
        if source is not None:
            stmt = stmt.where(Edge.source_id == source)
        if target is not None:
            stmt = stmt.where(Edge.target_id == target)
        edges = db.exec(stmt).all()
        data = [EdgeOut.model_validate(e).model_dump(by_alias=True) for e in edges]
        return success_response(data, {"total": len(data)})
    except OperationalError:
        return success_response([], {"total": 0, "db": "unavailable"})
