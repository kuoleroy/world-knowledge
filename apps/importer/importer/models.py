"""数据模型：种子、原始条目、标注结果、待入库节点。

节点字段名与 ``nodes`` 表列名一致（snake_case），便于直接 upsert 到 Directus。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

QID_PATTERN = re.compile(r"^Q[1-9]\d*$")


def wikidata_slug(qid: str) -> str:
    """Wikidata 条目的稳定 slug：``wd-Q12345``。

    slug 只由来源主键推导，不含标题，因此标题改写/翻译后 slug 不变，可安全用于
    URL 与幂等 upsert。
    """
    if not QID_PATTERN.match(qid):
        raise ValueError(f"非法 QID：{qid!r}")
    return f"wd-{qid}"


@dataclass(frozen=True)
class Seed:
    """一个学科下的种子条目（人工核对过的 Wikidata 根条目）。"""

    qid: str
    discipline: str
    tradition: str
    expect_zh: str = ""
    stage: str | None = None
    limit: int = 5
    min_sitelinks: int | None = None
    # 是否把「直接子类」也算进子树。概念型种子（中医、阿育吠陀）需要，
    # 学科/疾病型种子不需要——Wikidata 的 P279 边噪声很大（例如「免疫学」被标成
    # 「儿科学」的子类），默认关闭。
    include_subclasses: bool = False
    note: str = ""


@dataclass
class RawItem:
    """抓取到的原始条目；同一 QID 被多个种子命中时合并到这里。"""

    qid: str
    label_zh: str | None
    label_en: str | None
    desc_zh: str | None
    desc_en: str | None
    zhwiki_url: str | None
    enwiki_url: str | None
    sitelinks: int
    primary_seed: Seed
    seed_qids: set[str] = field(default_factory=set)

    @property
    def title(self) -> str | None:
        """节点标题：优先中文标签，其次英文标签。"""
        for value in (self.label_zh, self.label_en):
            if value and value.strip():
                return value.strip()
        return None

    @property
    def summary(self) -> str | None:
        """中文一句话描述（Wikidata description，CC0）。没有中文描述就留空。"""
        if self.desc_zh and self.desc_zh.strip():
            return self.desc_zh.strip()
        return None

    @property
    def corpus(self) -> str:
        """标注规则匹配用的语料：中英文标签 + 描述，已小写化。"""
        parts = [self.label_zh, self.label_en, self.desc_zh, self.desc_en]
        return " ".join(part.casefold() for part in parts if part)

    @property
    def wikipedia_url(self) -> str | None:
        """source_url：优先中文维基条目（署名入口），其次英文。"""
        return self.zhwiki_url or self.enwiki_url


@dataclass(frozen=True)
class Annotation:
    """标注结果，附可复核的依据。"""

    discipline: str
    stage: str
    tradition: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class NodeDraft:
    """待写入 nodes 表的一条记录（列名与表结构一致）。"""

    slug: str
    type: str
    title: str
    summary: str | None
    stage: str
    discipline: str
    tradition: str
    language: str
    status: str
    source_id: str
    source_url: str | None

    def to_row(self) -> dict[str, Any]:
        """转成 Directus ``/items/nodes`` 的请求体字段。"""
        return {
            "slug": self.slug,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "stage": self.stage,
            "discipline": self.discipline,
            "tradition": self.tradition,
            "language": self.language,
            "status": self.status,
            "source_id": self.source_id,
            "source_url": self.source_url,
        }
