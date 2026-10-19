"""nodes 索引的构建逻辑：一次性全量索引，不做实时同步。

数据源是 MySQL：``nodes`` 表（与 /v1/nodes 同一只读映射）+ ``contents`` 表的最新
正文。文档形状用 ``NodeOut`` 序列化，保证与共享类型 KnowledgeNode 对齐；正文以
``bodyText``（``body_ref`` 剥出的纯文本）附加进文档，只参与检索，**不改变
/v1/search 的 data 形状**（见 ``app/services/search.py``）。

``contents`` 为空、正文引用不可解、甚至 contents 表还不存在时，都只是「没有正文」，
索引照常完成。
"""

import logging
from collections.abc import Sequence
from typing import Any

from meilisearch import Client
from meilisearch.errors import MeilisearchApiError, MeilisearchError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.db.session import get_engine
from app.models.content import Content
from app.models.node import Node
from app.schemas.node import NodeOut
from app.services.body_text import body_text
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


def to_document(node: Node, body_text_value: str | None = None) -> dict[str, Any]:
    """把 ORM 节点转成索引文档（camelCase，日期转 ISO 字符串）。

    有正文时补 ``bodyText``；取不到正文则不写该字段（Meilisearch 里缺省即空）。
    """
    document = NodeOut.model_validate(node).model_dump(mode="json", by_alias=True)
    if body_text_value:
        document["bodyText"] = body_text_value
    return document


def load_body_texts(session: Session) -> dict[int, str]:
    """读 ``contents``，按节点取**最新版本**正文并剥成纯文本。

    与门户取值口径一致（13.8：``sort=-version, limit=1``）：每个 ``node`` 只取
    ``version`` 最大的一条；正文为空 / 不可解 / 表不存在时该节点直接缺席。
    """
    try:
        contents = session.exec(
            select(Content).order_by(Content.node, Content.version.desc())
        ).all()
    except SQLAlchemyError as exc:
        # contents 表由 Directus 建；缺表 / 查询失败时降级为「本次没有正文」
        logger.warning("读取 contents 失败，本次不索引正文：%s", exc)
        return {}

    texts: dict[int, str] = {}
    seen: set[int] = set()
    for content in contents:
        node_id = content.node
        if node_id in seen:
            continue
        seen.add(node_id)
        text = body_text(content.body_ref)
        if text:
            texts[node_id] = text
    return texts


def load_documents() -> list[dict[str, Any]]:
    """从 MySQL 读取全部节点（含正文纯文本）并转成索引文档。"""
    with Session(get_engine()) as session:
        nodes = session.exec(select(Node).order_by(Node.id)).all()
        body_texts = load_body_texts(session)
    return [
        to_document(node, body_texts.get(node.id) if node.id is not None else None)
        for node in nodes
    ]


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
    exists = True
    try:
        client.get_index(NODES_INDEX_UID)
    except MeilisearchApiError as exc:
        if exc.code != "index_not_found":
            raise
        exists = False

    # 删除也走异步任务；索引本就不存在时再删会得到一个失败任务，故先探测再删
    if reset and exists:
        _wait(client, client.delete_index(NODES_INDEX_UID))
        exists = False

    if not exists:
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
    """全量重建：读 MySQL（nodes + 最新正文）→ 建索引 / 更新 settings → 批量写入。"""
    documents = load_documents()
    client = get_client()
    ensure_index(client, reset=reset)
    indexed = index_nodes(client, documents, batch_size=batch_size)
    with_body = sum(1 for document in documents if document.get("bodyText"))
    logger.info("nodes 索引完成：%s 条（含正文 %s 条）", indexed, with_body)
    return {
        "index": NODES_INDEX_UID,
        "documents": indexed,
        "documentsWithBodyText": with_body,
        "reset": reset,
    }
