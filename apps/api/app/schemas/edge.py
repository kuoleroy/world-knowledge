"""关系边的响应模型（只读；增删改由 Directus 负责）。"""

from app.schemas.common import CamelModel


class EdgeOut(CamelModel):
    """边响应（形状对应共享类型 KnowledgeEdge）。"""

    id: int
    source_id: int
    target_id: int
    relation: str
    weight: float | None = None
