"""关系边的响应模型（只读；增删改由 Directus 负责）。"""

from datetime import datetime

from app.schemas.common import CamelModel


class EdgeOut(CamelModel):
    """边响应。"""

    id: int
    source_id: int
    target_id: int
    type: str
    label: str | None = None
    description: str | None = None
    created_at: datetime | None = None
