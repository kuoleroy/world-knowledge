"""SQLModel engine / session 管理。

关键设计：**懒连接**。引擎与 Session 在首次使用时才创建，
`create_engine` 本身不会真正连接数据库，因此数据库未启动时，
依赖骨架 JSON 的接口（stages / disciplines / traditions）仍可用。

说明：表结构由 **Directus** 建并管理；这里只用 SQLModel 做**只读映射**，
**不使用 Alembic**（见项目文档 4.2 / 6.2）。
"""

from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """懒加载数据库引擎（首次调用时才创建，不建立真实连接）。"""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话，请求结束后关闭。"""
    with Session(get_engine()) as session:
        yield session
