"""nodes 索引的构建逻辑：一次性全量索引，不做实时同步。

数据源是 MySQL 中的 ``nodes`` 表（与 /v1/nodes 同一只读映射），
文档形状用 ``NodeOut`` 序列化，保证与共享类型 KnowledgeNode 对齐。
"""

import logging
from collections.abc import Sequence
from typing import Any

from meilisearch import Client
from meilisearch.errors import MeilisearchApiError, MeilisearchError
from sqlmodel import Session, select

from app.db.session import get_engine
from app.models.node import Node
from app.schemas.node import NodeOut
from app.services.meilisearch_client import (
    NODES_INDEX_UID,
    NODES_PRIMARY_KEY,
    get_client,
    nodes_index_settings,
)

logger = logging.getLogger(__name__)

# 单批推送条数：60 条量级一次即可，留大值便于后续增长
DEFAULT_BATCH_SIZE = 500
# 等待单个 Meilisearch 异步任务的超时（毫秒）
TASK_TIMEOUT_MS = 60_000


def to_document(node: Node) -> dict[str, Any]:
    """把 ORM 节点转成索引文档（camelCase，日期转 ISO 字符串）。"""
    return NodeOut.model_validate(node).model_dump(mode="json", by_alias=True)


def load_documents() -> list[dict[str, Any]]:
    """从 MySQL 读取全部节点并转成索引文档。"""
    with Session(get_engine()) as session:
        nodes = session.exec(select(Node).order_by(Node.id)).all()
    return [to_document(node) for node in nodes]


def _wait(client: Client, task_info: Any, *, timeout_ms: int = TASK_TIMEOUT_MS) -> None:
    """等待异步任务完成；失败即抛出，避免「假成功」。"""
    task = client.wait_for_task(task_info.task_uid, timeout_in_ms=timeout_ms)
    if task.status != "succeeded":
        error = task.error or {}
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise MeilisearchError(
            f"Meilisearch 任务 {task.type} 未成功：{task.status} {message or ''}".strip()
        )


def ensure_index(client: Client, *, reset: bool = False) -> None:
    """确保 nodes 索引存在且 settings 与契约一致。

    ``reset=True`` 时先删除索引再重建（settings 或字段变更后使用）。
    """
    if reset:
        try:
            _wait(client, client.delete_index(NODES_INDEX_UID))
        except MeilisearchApiError as exc:
            # 索引本来就不存在：等价于已重置
            if exc.code != "index_not_found":
                raise

    try:
        client.get_index(NODES_INDEX_UID)
    except MeilisearchApiError as exc:
        if exc.code != "index_not_found":
            raise
        _wait(client, client.create_index(NODES_INDEX_UID, {"primaryKey": NODES_PRIMARY_KEY}))

    _wait(client, client.index(NODES_INDEX_UID).update_settings(nodes_index_settings()))


def index_nodes(
    client: Client,
    documents: Sequence[dict[str, Any]],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """分批覆盖写入索引文档，等全部任务完成后返回写入条数。"""
    index = client.index(NODES_INDEX_UID)
    size = max(1, batch_size)
    for start in range(0, len(documents), size):
        batch = documents[start : start + size]
        _wait(client, index.add_documents(batch, primary_key=NODES_PRIMARY_KEY))
    return len(documents)


def rebuild_index(
    *,
    reset: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """全量重建：读 MySQL → 建索引 / 更新 settings → 批量写入。"""
    documents = load_documents()
    client = get_client()
    ensure_index(client, reset=reset)
    indexed = index_nodes(client, documents, batch_size=batch_size)
    logger.info("nodes 索引完成：%s 条", indexed)
    return {"index": NODES_INDEX_UID, "documents": indexed, "reset": reset}
