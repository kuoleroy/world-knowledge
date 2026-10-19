"""知识节点的响应模型（只读；增删改由 Directus 负责）。"""

from datetime import datetime

from app.schemas.common import CamelModel


class NodeOut(CamelModel):
    """节点响应。"""

    id: int
    type: str
    slug: str
    title: str
    summary: str | None = None
    stage: str | None = None
    discipline: str | None = None
    tradition: str
    language: str
    status: str
    source_id: str | None = None
    source_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
