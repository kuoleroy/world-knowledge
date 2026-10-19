"""搜索服务：查询 nodes 索引。

只负责「查得到」的正常路径；Meilisearch 不可达时 SDK 异常原样抛出，
由接口层降级为空结果（见 app/api/v1/search.py）。
"""

from typing import Any

from meilisearch import Client

from app.services.meilisearch_client import NODES_INDEX_UID

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def normalize_limit(limit: int) -> int:
    """把 limit 收敛到 [1, MAX_LIMIT]，避免非法值触发 422 或超大结果集。"""
    return max(1, min(limit, MAX_LIMIT))


def _escape_filter_value(value: str) -> str:
    """转义 filter 表达式里的字符串字面量（反斜杠与双引号）。"""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_filter(
    discipline: str | None = None,
    stage: str | None = None,
    tradition: str | None = None,
) -> str | None:
    """把可选过滤维度拼成 Meilisearch filter 表达式；无过滤条件时返回 None。"""
    conditions: list[str] = []
    for field, value in (
        ("discipline", discipline),
        ("stage", stage),
        ("tradition", tradition),
    ):
        if value:
            conditions.append(f'{field} = "{_escape_filter_value(value)}"')
    return " AND ".join(conditions) or None


def search_nodes(
    client: Client,
    *,
    query: str,
    limit: int,
    discipline: str | None = None,
    stage: str | None = None,
    tradition: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """按关键词 + 过滤维度查询 nodes 索引，返回 (命中节点数组, meta)。

    索引文档即 NodeOut（camelCase），命中结果与 /v1/nodes 的元素形状一致。
    """
    params: dict[str, Any] = {"limit": normalize_limit(limit)}
    filter_expression = build_filter(discipline, stage, tradition)
    if filter_expression:
        params["filter"] = filter_expression

    result = client.index(NODES_INDEX_UID).search(query or "", params)
    hits = result.get("hits") or []
    # 去掉 _formatted / _matchesPosition 等 Meilisearch 内部字段（当前未请求，防御性处理）
    data = [
        {key: value for key, value in hit.items() if not key.startswith("_")}
        for hit in hits
    ]

    meta: dict[str, Any] = {
        "query": query,
        "limit": params["limit"],
        "total": result.get("estimatedTotalHits", len(data)),
        "degraded": False,
    }
    if filter_expression:
        meta["filter"] = filter_expression
    return data, meta
