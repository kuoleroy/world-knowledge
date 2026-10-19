"""知识节点接口：只读（走 MySQL；增删改由 Directus 负责）。

数据库未启动时优雅降级：读接口返回空列表（不报 500）。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from app.db.session import get_db
from app.models.node import Node
from app.schemas.common import error_response, success_response
from app.schemas.node import NodeOut

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("")
def list_nodes(
    type: str | None = None,
    stage: str | None = None,
    discipline: str | None = None,
    tradition: str | None = None,
    slug: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """节点列表，可按 type / stage / discipline / tradition / slug 过滤（只读）。"""
    try:
        stmt = select(Node)
        if type is not None:
            stmt = stmt.where(Node.type == type)
        if stage is not None:
            stmt = stmt.where(Node.stage == stage)
        if discipline is not None:
            stmt = stmt.where(Node.discipline == discipline)
        if tradition is not None:
            stmt = stmt.where(Node.tradition == tradition)
        if slug is not None:
            stmt = stmt.where(Node.slug == slug)
        nodes = db.exec(stmt).all()
        data = [NodeOut.model_validate(n).model_dump(by_alias=True) for n in nodes]
        return success_response(data, {"total": len(data)})
    except OperationalError:
        # 数据库未启动：懒连接下骨架接口不受影响，此处降级为空列表
        return success_response([], {"total": 0, "db": "unavailable"})


@router.get("/{node_id}")
def get_node_detail(node_id: int, db: Session = Depends(get_db)) -> dict:
    """按 id 获取节点（只读）。"""
    try:
        node = db.get(Node, node_id)
    except OperationalError:
        return error_response("数据库不可用", {"db": "unavailable"})
    if node is None:
        raise HTTPException(status_code=404, detail=f"节点不存在: {node_id}")
    return success_response(NodeOut.model_validate(node).model_dump(by_alias=True))
