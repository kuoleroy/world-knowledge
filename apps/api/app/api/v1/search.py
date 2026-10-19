"""搜索接口：GET /v1/search（Meilisearch nodes 索引）。

Meilisearch 不可达 / 索引未建时**不报 500**：返回空结果并置
``meta.degraded=true``，门户据此降级提示（与 /v1/nodes 的 DB 降级一致）。
"""

import logging

from fastapi import APIRouter
from meilisearch.errors import MeilisearchError

from app.schemas.common import success_response
from app.services.meilisearch_client import get_client
from app.services.search import DEFAULT_LIMIT, normalize_limit, search_nodes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def _degraded(query: str, limit: int, reason: str) -> dict:
    """搜索服务不可用时的降级响应：空结果 + degraded 标记。"""
    return success_response(
        [],
        {"query": query, "limit": limit, "total": 0, "degraded": True, "reason": reason},
    )


@router.get("")
def search(
    q: str = "",
    limit: int = DEFAULT_LIMIT,
    discipline: str | None = None,
    stage: str | None = None,
    tradition: str | None = None,
) -> dict:
    """全文搜索节点；q 为空时按过滤条件浏览（等价于取前 limit 条）。"""
    safe_limit = normalize_limit(limit)
    try:
        data, meta = search_nodes(
            get_client(),
            query=q,
            limit=safe_limit,
            discipline=discipline,
            stage=stage,
            tradition=tradition,
        )
    except (MeilisearchError, OSError) as exc:
        logger.warning("搜索降级（Meilisearch 不可用）：%s", exc)
        # 不把内部地址/堆栈透给客户端，详细原因只进日志
        return _degraded(q, safe_limit, "Meilisearch 不可达或索引不可用")
    return success_response(data, meta)
