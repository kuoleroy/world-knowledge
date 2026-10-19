"""内容正文模型（SQLModel，只读映射 Directus 建的表）。

正文文件本身以文件系统 + Git 版本管理，MySQL 存索引与元信息。
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Content(SQLModel, table=True):
    """节点内容正文。"""

    __tablename__ = "contents"

    id: int | None = Field(default=None, primary_key=True)
    node_id: int = Field(index=True, foreign_key="nodes.id")
    language: str = Field(default="zh", max_length=16)
    # 正文格式，如 mdx / markdown
    format: str = Field(default="mdx", max_length=32)
    # 正文内容
    body: str | None = Field(default=None)
    # 正文文件路径（文件系统）
    file_path: str | None = Field(default=None, max_length=512)
    version: int = Field(default=1)
    status: str = Field(default="draft", index=True, max_length=32)

    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
