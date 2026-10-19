"""内容正文模型（SQLModel，只读映射 Directus 建的表）。

正文文件本身以文件系统 + Git 版本管理，MySQL 只存引用与元信息。
Directus 建的列名以项目文档 4.2 为准：`id, node, body_ref, format, version, checksum, status`。
"""

from sqlmodel import Field, SQLModel


class Content(SQLModel, table=True):
    """节点内容正文的索引与元信息。"""

    __tablename__ = "contents"

    id: int | None = Field(default=None, primary_key=True)
    # 所属节点（列名 node，指向 nodes.id）
    node: int = Field(index=True, foreign_key="nodes.id")
    # 正文引用：正文文件在文件系统中的路径（如 content/dao.mdx）
    body_ref: str | None = Field(default=None, max_length=512)
    # 正文格式，如 mdx / markdown
    format: str = Field(default="mdx", max_length=32)
    # 正文版本号（正文由 Git 管理，这里只记录版本）
    version: int = Field(default=1)
    # 正文校验和（sha256），用于校验引用文件与记录是否一致
    checksum: str | None = Field(default=None, max_length=64)
    # 状态：draft / review / published
    status: str = Field(default="draft", index=True, max_length=32)
