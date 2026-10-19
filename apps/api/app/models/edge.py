"""知识关系边模型（SQLModel，只读映射 Directus 建的表）。"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Edge(SQLModel, table=True):
    """节点之间的关系边。"""

    __tablename__ = "edges"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(index=True, foreign_key="nodes.id")
    target_id: int = Field(index=True, foreign_key="nodes.id")
    # 关系类型，如 prerequisite / related / contrasts / part_of（含跨知识传统的并列关系）
    type: str = Field(index=True, max_length=64)
    label: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)

    created_at: datetime | None = Field(default=None)
