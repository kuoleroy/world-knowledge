"""Meilisearch 客户端与索引契约。

用官方 ``meilisearch`` SDK（MIT，见 requirements.txt），不自己封装 REST。
索引契约同时供「一次性全量索引」与「搜索端点」使用，避免两处漂移。
"""

from functools import lru_cache

from meilisearch import Client

from app.core.config import settings

# ---- 索引契约（文档形状对齐 packages/types 的 KnowledgeNode）----
NODES_INDEX_UID = "nodes"
NODES_PRIMARY_KEY = "id"

# 参与相关性排序的字段：标题 / 摘要 / 正文纯文本（08 把 contents 正文纳入搜索）
NODES_SEARCHABLE_ATTRIBUTES = ["title", "summary", "bodyText"]

# 可过滤维度（任务书要求）
NODES_FILTERABLE_ATTRIBUTES = ["discipline", "stage", "tradition"]

# 命中结果随文档返回的字段：覆盖 NodeOut 全部字段，
# 保证 /v1/search 的 data 直接就是 KnowledgeNode 形状（门户可直接复用 NodeList）。
# ``bodyText`` 也列在这里：Meilisearch 只对 displayedAttributes 里的字段做 crop /
# highlight（片段在 _formatted 里下发），端点取完片段后会把它从 data 中剔除。
NODES_DISPLAYED_ATTRIBUTES = [
    "id",
    "type",
    "slug",
    "title",
    "summary",
    "bodyText",
    "stage",
    "discipline",
    "tradition",
    "language",
    "status",
    "sourceId",
    "sourceUrl",
    "createdAt",
    "updatedAt",
]

# 单次请求超时（秒，requests 语义）：Meilisearch 不可达时快速失败，交给接口降级
REQUEST_TIMEOUT_SECONDS = 5


@lru_cache
def get_client() -> Client:
    """进程内复用 Meilisearch 客户端（首次调用才创建，不发起真实连接）。"""
    return Client(
        settings.MEILISEARCH_HOST,
        settings.MEILISEARCH_API_KEY or None,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def nodes_index_settings() -> dict[str, list[str]]:
    """nodes 索引的 settings（建索引与重建时共用同一份契约）。"""
    return {
        "searchableAttributes": NODES_SEARCHABLE_ATTRIBUTES,
        "filterableAttributes": NODES_FILTERABLE_ATTRIBUTES,
        "displayedAttributes": NODES_DISPLAYED_ATTRIBUTES,
    }
