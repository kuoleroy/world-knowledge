"""正文取文：把 ``contents.body_ref`` 解析成可进索引的纯文本。

``body_ref`` 按项目文档 13.8 三选一，与门户 ``apps/web/lib/api/contents.ts`` 的
解析顺序保持一致：

1. **原始 MDX 字符串** → 直接剥成纯文本；
2. **Directus 文件 UUID** → 取 ``{DIRECTUS_URL}/assets/<uuid>`` 后剥成纯文本；
3. **``http(s)`` 链接** → 下载后剥成纯文本。

**文件系统路径**在容器里读不到，视为不可解；任何取文失败（网络 / 404 / 编码）
都只记日志、返回 ``None``，由调用方跳过该节点——**正文缺失不许让 reindex 失败**。
"""

import html
import logging
import re
import urllib.request
from urllib.parse import urlsplit

from app.core.config import settings

logger = logging.getLogger(__name__)

# 单篇正文进索引的字符上限：正文引用本身是 varchar(512)，此上限只防御 URL / 文件型正文
MAX_BODY_TEXT_CHARS = 20_000
# 取远程正文的超时（秒）：不可达时快速放弃，不拖住整次 reindex
FETCH_TIMEOUT_SECONDS = 5
USER_AGENT = "world-knowledge-api/0.1 (contents indexer)"

# 与门户一致的引用形态判定（见 13.8）
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
HTTP_RE = re.compile(r"^https?://", re.I)
FILE_PATH_RE = re.compile(r"\.(md|mdx)$", re.I)

# ---- MDX / Markdown 剥文用的规则 ----
_FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---[ \t]*\r?\n?", re.S)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_JSX_COMMENT_RE = re.compile(r"\{/\*.*?\*/\}", re.S)
# MDX 顶部的 import / export（05 的正文没有，防御性处理）
_ESM_LINE_RE = re.compile(r"^[ \t]*(?:import|export)\b[^\n]*$", re.M)
# 代码围栏标记去掉、代码本体保留（对「某概念怎么写」之类查询仍有意义）
_FENCE_RE = re.compile(r"^[ \t]*(?:```|~~~)[^\n]*$", re.M)
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)\n]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)\n]*\)")
_INLINE_CODE_RE = re.compile(r"`([^`\n]*)`")
# JSX / HTML 标签（含自闭合、带属性的 MDX 组件）
_TAG_RE = re.compile(r"</?[A-Za-z][^<>\n]*>")
_TABLE_SEPARATOR_RE = re.compile(
    r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$", re.M
)
_HR_RE = re.compile(r"^[ \t]{0,3}([-*_])[ \t]*(?:\1[ \t]*){2,}$", re.M)
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]*", re.M)
_BLOCKQUOTE_RE = re.compile(r"^[ \t]{0,3}>[ \t]?", re.M)
_LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]+", re.M)
_PIPE_RE = re.compile(r"[ \t]*\|[ \t]*")
_EMPHASIS_RE = re.compile(r"(\*\*|__|~~|\*|_)(?=\S)(.+?)(?<=\S)\1")


def resolve_body_ref(ref: str | None) -> str | None:
    """把 ``body_ref`` 解析成正文源文本；不可解时返回 ``None``。

    返回的可能是 MDX 源（第 1 种形态）或下载到的远程文本（第 2、3 种形态），
    都还没剥成纯文本。
    """
    value = (ref or "").strip()
    if not value:
        return None
    if UUID_RE.match(value):
        return _fetch_text(f"{settings.DIRECTUS_URL.rstrip('/')}/assets/{value}")
    if HTTP_RE.match(value):
        return _fetch_text(value)
    # 文件系统路径：容器内读不到（13.8 明确「不可渲染」）
    if "\n" not in value and FILE_PATH_RE.search(value):
        return None
    return value


def mdx_to_plain_text(source: str) -> str:
    """把 MDX / Markdown 剥成单行纯文本（保留可读的中文正文）。"""
    text = source.lstrip("\ufeff")
    text = _FRONTMATTER_RE.sub("", text)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _JSX_COMMENT_RE.sub("", text)
    text = _ESM_LINE_RE.sub("", text)
    text = _FENCE_RE.sub("", text)
    text = _IMAGE_RE.sub(r"\1", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _TAG_RE.sub(" ", text)
    text = _TABLE_SEPARATOR_RE.sub("", text)
    text = _HR_RE.sub("", text)
    text = _HEADING_RE.sub("", text)
    text = _BLOCKQUOTE_RE.sub("", text)
    text = _LIST_MARKER_RE.sub("", text)
    text = _PIPE_RE.sub(" ", text)
    text = _EMPHASIS_RE.sub(r"\2", text)
    text = html.unescape(text)
    # 段落 / 列表项之间保持空格分隔，便于 Meilisearch 分词
    return " ".join(text.split())


def body_text(ref: str | None) -> str | None:
    """``body_ref`` → 纯文本；取不到文本时返回 ``None``（调用方跳过该节点）。"""
    source = resolve_body_ref(ref)
    if source is None:
        return None
    text = mdx_to_plain_text(source)
    if not text:
        return None
    return text[:MAX_BODY_TEXT_CHARS]


def _fetch_text(url: str) -> str | None:
    """下载远程正文；失败只记日志并返回 ``None``（不抛异常）。"""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = response.read()
    except (OSError, ValueError) as exc:
        # HTTPError / URLError 都是 OSError 子类；日志里去掉查询串免得泄露签名
        logger.warning("正文引用取不到，已跳过：%s（%s）", _safe_url(url), exc)
        return None
    return payload.decode(charset, errors="replace")


def _safe_url(url: str) -> str:
    """日志用：保留 scheme / host / path，丢掉查询串。"""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"
