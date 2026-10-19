"""搜索服务：查询 nodes 索引。

只负责「查得到」的正常路径；Meilisearch 不可达时 SDK 异常原样抛出，
由接口层降级为空结果（见 app/api/v1/search.py）。

正文（``bodyText``）只用于检索与命中片段：``data`` 里会剔除该字段（保持
KnowledgeNode 形状），片段以 ``meta.snippets``（``{节点 id: 带 <em> 的片段}``）
随响应下发，门户据此在结果卡里显示正文摘录。
"""

from typing import Any

from meilisearch import Client

from app.services.meilisearch_client import NODES_INDEX_UID

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# 片段参数：cropLength 以「词」计，命中时 Meilisearch 会在命中词附近取窗
SNIPPET_ATTRIBUTE = "bodyText"
SNIPPET_CROP_LENGTH = 30
SNIPPET_CROP_MARKER = "…"
# 下发前再按可见字符收敛一次（中文正文按词裁剪可能仍偏长）
MAX_SNIPPET_CHARS = 200
EM_OPEN = "<em>"
EM_CLOSE = "</em>"


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


def trim_snippet(markup: str, limit: int = MAX_SNIPPET_CHARS) -> str:
    """把带 ``<em>`` 高亮标记的片段裁到 limit 个可见字符。

    只认自己写入的 ``<em>`` / ``</em>`` 两个标签；裁剪落在标签内时补闭合标签，
    免得门户高亮解析错乱。其余字符（含正文里的 ``<``）原样当文本返回。
    """
    text = markup.strip()
    if not text:
        return ""
    parts: list[str] = []
    visible = 0
    index = 0
    highlighted = False
    while index < len(text) and visible < limit:
        if text.startswith(EM_OPEN, index):
            parts.append(EM_OPEN)
            highlighted = True
            index += len(EM_OPEN)
        elif text.startswith(EM_CLOSE, index):
            parts.append(EM_CLOSE)
            highlighted = False
            index += len(EM_CLOSE)
        else:
            parts.append(text[index])
            visible += 1
            index += 1
    if highlighted:
        parts.append(EM_CLOSE)
    snippet = "".join(parts)
    return f"{snippet}{SNIPPET_CROP_MARKER}" if index < len(text) else snippet


def _split_hit(hit: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """拆一条命中：``data`` 用文档（去掉内部字段与 bodyText），另取正文片段。"""
    formatted = hit.get("_formatted")
    snippet = formatted.get(SNIPPET_ATTRIBUTE) if isinstance(formatted, dict) else None
    document = {key: value for key, value in hit.items() if not key.startswith("_")}
    document.pop(SNIPPET_ATTRIBUTE, None)
    return document, snippet if isinstance(snippet, str) else None


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

    索引文档即 NodeOut（camelCase）+ bodyText，命中结果与 /v1/nodes 的元素形状一致；
    正文片段单独放在 ``meta.snippets`` 里。
    """
    params: dict[str, Any] = {"limit": normalize_limit(limit)}
    filter_expression = build_filter(discipline, stage, tradition)
    if filter_expression:
        params["filter"] = filter_expression
    # 正文片段：由 Meilisearch 裁剪并高亮命中词，结果只在 _formatted 里
    params["attributesToCrop"] = [SNIPPET_ATTRIBUTE]
    params["cropLength"] = SNIPPET_CROP_LENGTH
    params["cropMarker"] = SNIPPET_CROP_MARKER
    params["attributesToHighlight"] = [SNIPPET_ATTRIBUTE]

    result = client.index(NODES_INDEX_UID).search(query or "", params)
    hits = result.get("hits") or []

    data: list[dict[str, Any]] = []
    snippets: dict[str, str] = {}
    for hit in hits:
        document, snippet = _split_hit(hit)
        data.append(document)
        trimmed = trim_snippet(snippet) if snippet else ""
        if trimmed and "id" in document:
            snippets[str(document["id"])] = trimmed

    meta: dict[str, Any] = {
        "query": query,
        "limit": params["limit"],
        "total": result.get("estimatedTotalHits", len(data)),
        "degraded": False,
    }
    if filter_expression:
        meta["filter"] = filter_expression
    if snippets:
        meta["snippets"] = snippets
    return data, meta
