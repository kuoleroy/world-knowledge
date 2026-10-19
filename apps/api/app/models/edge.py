"""知识关系边模型（SQLModel，只读映射 Directus 建的表）。

Directus 建的列名以项目文档 4.2 为准：`id, source_node, target_node, relation, weight`；
这里用 `Column` 把 ORM 属性显式映射到真实列名（只读，不使用 Alembic 建表）。
"""

from sqlalchemy import Column, Integer

from sqlmodel import Field, SQLModel


class Edge(SQLModel, table=True):
    """节点之间的关系边。"""

    __tablename__ = "edges"

    id: int | None = Field(default=None, primary_key=True)
    # 起点节点（列名 source_node，指向 nodes.id）
    source_id: int = Field(sa_column=Column("source_node", Integer, index=True, nullable=False))
    # 终点节点（列名 target_node，指向 nodes.id）
    target_id: int = Field(sa_column=Column("target_node", Integer, index=True, nullable=False))
    # 关系类型，如 prerequisite / related / contrasts / part_of（含跨知识传统的并列关系）
    relation: str = Field(index=True, max_length=64)
    # 关系权重（可选，用于排序 / 强度）
    weight: float | None = Field(default=None)
