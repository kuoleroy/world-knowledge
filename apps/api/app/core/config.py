"""应用配置：使用 pydantic-settings 从 .env 读取环境变量。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项，字段名对应环境变量（大小写不敏感）。"""

    # 项目信息
    PROJECT_NAME: str = "WorldKnowledge API"
    API_V1_PREFIX: str = "/v1"

    # 数据库连接串（MySQL，表结构由 Directus 建并管理），数据库未启动时也应可加载配置
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/world_knowledge"

    # Directus（headless CMS：管数据、出 REST/GraphQL、管用户权限）
    DIRECTUS_URL: str = "http://localhost:8055"
    DIRECTUS_KEY: str = ""
    DIRECTUS_SECRET: str = ""

    # 搜索（后期接入 Meilisearch）
    MEILISEARCH_HOST: str = "http://localhost:7700"
    MEILISEARCH_API_KEY: str = ""

    # 图谱（后期接入 Neo4j）
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # 跨域（门户 web :3000、后台 Directus :8055）
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8055"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """将逗号分隔的 CORS 配置解析为列表。"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """获取单例配置对象。"""
    return Settings()


settings = get_settings()
