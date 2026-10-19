"""写入库的后端（步骤 4）。

当前只实现 Directus REST 一种：写入口唯一、不持数据库凭据、权限与审计交给 Directus。
另需直连 MySQL 时再加一个同接口的实现即可（``ensure_collection`` / ``upsert_many``）。
"""

from .directus import DirectusError, DirectusWriter, UpsertOutcome

__all__ = ["DirectusError", "DirectusWriter", "UpsertOutcome"]
