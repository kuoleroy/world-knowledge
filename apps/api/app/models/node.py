"""知识节点模型（SQLModel，只读映射 Directus 建的表）。

表结构由 Directus 建并管理，这里只做映射读取（见项目文档 4.2）。
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Node(SQLModel, table=True):
    """知识节点。

    - stage / discipline 引用骨架定义（JSON）
    - tradition 为节点级知识传统标签（与主流科学线平级并列）
    """

    __tablename__ = "nodes"

    id: int | None = Field(default=None, primary_key=True)
    # 节点类型，如 concept / path / resource / topic
    type: str = Field(index=True, max_length=64)
    # 稳定标识（用于 URL / 引用）
    slug: str = Field(index=True, unique=True, max_length=255)
    title: str = Field(max_length=255)
    summary: str | None = Field(default=None)

    # 归属维度：阶段 / 学科（引用骨架定义）
    stage: str | None = Field(default=None, index=True, max_length=64)
    discipline: str | None = Field(default=None, index=True, max_length=64)
    # 知识传统标签：empirical / holistic / experiential / speculative / devotional
    tradition: str = Field(default="empirical", index=True, max_length=64)

    language: str = Field(default="zh", max_length=16)
    # 状态：draft / review / published
    status: str = Field(default="draft", index=True, max_length=32)

    # 来源开放知识库（见项目文档 4.4）
    source_id: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1024)

    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
