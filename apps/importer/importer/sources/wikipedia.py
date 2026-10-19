"""Wikipedia 抓取：条目正文摘要，只作改写 / 翻译素材。

**注意许可**：维基百科正文是 CC BY-SA 4.0，直接搬运需要署名并以相同许可共享。
因此这里的摘要**不写入** ``nodes.summary``（那里放的是 Wikidata 描述，CC0），
而是单独落盘到 ``out/<discipline>/wiki/<slug>.json``，连同来源链接与许可信息一起，
供后续人工改写时使用；发布时必须保留对原条目及其编辑者的署名。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import quote, unquote

from ..config import SourcesConfig
from ..net import Fetcher


@dataclass(frozen=True)
class WikiSummary:
    """一条维基百科摘要素材。"""

    lang: str
    title: str
    extract: str
    url: str | None
    description: str | None
    license: str
    attribution: str
    retrieved_at: str

    def to_json(self) -> dict[str, Any]:
        return {
            "lang": self.lang,
            "title": self.title,
            "extract": self.extract,
            "url": self.url,
            "description": self.description,
            "license": self.license,
            "attribution": self.attribution,
            "retrieved_at": self.retrieved_at,
            "note": "改写素材，非最终文案；发布时须署名并遵循 CC BY-SA 4.0",
        }


def title_from_url(url: str) -> str | None:
    """从维基条目 URL 取标题（``/wiki/%E4%B8%AD%E5%8C%BB%E5%AD%A6`` → ``中医学``）。"""
    if not url:
        return None
    slug = unquote(url.rstrip("/").rsplit("/", 1)[-1])
    if not slug:
        return None
    return slug.replace("_", " ")


def fetch_summary(
    fetcher: Fetcher,
    sources: SourcesConfig,
    *,
    lang: str,
    title: str,
) -> WikiSummary | None:
    """取一条条目的摘要；条目不存在（404）返回 ``None``。"""
    if not title:
        return None
    endpoint = sources.wikipedia_endpoint.format(
        lang=lang,
        title=quote(title.replace(" ", "_"), safe=""),
    )
    payload = fetcher.get_json(endpoint, ignore_status=(404,))
    if payload is None:
        return None
    extract = payload.get("extract")
    if not isinstance(extract, str) or not extract.strip():
        return None

    content_urls = payload.get("content_urls")
    page_url: str | None = None
    if isinstance(content_urls, Mapping):
        desktop = content_urls.get("desktop")
        if isinstance(desktop, Mapping):
            candidate = desktop.get("page")
            if isinstance(candidate, str):
                page_url = candidate

    return WikiSummary(
        lang=lang,
        title=str(payload.get("title") or title),
        extract=extract.strip(),
        url=page_url,
        description=str(payload.get("description") or "").strip() or None,
        license=sources.wikipedia_license,
        attribution=sources.wikipedia_attribution,
        retrieved_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
