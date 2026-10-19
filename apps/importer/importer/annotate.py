"""标注：把抓到的条目映射到 stage × discipline × tradition。

规则全部来自 ``config/taxonomy.yaml``（可读、可改、人工可校正），本模块不含任何硬编码
关键词。每条标注都带 ``reasons``，写进 ``annotations.jsonl`` 便于复核与申诉。
"""

from __future__ import annotations

from .config import Rule, Taxonomy
from .models import Annotation, NodeDraft, RawItem, wikidata_slug


def annotate(item: RawItem, taxonomy: Taxonomy) -> Annotation:
    """按规则标注单条条目；先命中者胜，全不命中则回退种子默认值。"""
    corpus = item.corpus
    reasons: list[str] = []

    discipline = item.primary_seed.discipline
    reasons.append(f"discipline={discipline} ← 种子 {item.primary_seed.qid} 的学科归属")

    tradition_hit = _first_match(taxonomy.tradition_rules, corpus)
    if tradition_hit is not None:
        rule, keyword = tradition_hit
        tradition = rule.target
        reasons.append(f"tradition={tradition} ← 关键词「{keyword}」命中规则：{rule.reason}")
    else:
        tradition = item.primary_seed.tradition
        reasons.append(f"tradition={tradition} ← 无规则命中，继承种子 {item.primary_seed.qid} 的默认传统")

    # 种子上的 stage 只钉住「种子条目本身」：阶段是编辑判断，硬塞给整棵子树会把
    # 上游噪声（例如被误标成儿科学子类的「免疫学」）一起染成学前阶段。
    if item.primary_seed.stage and item.qid == item.primary_seed.qid:
        stage = item.primary_seed.stage
        reasons.append(f"stage={stage} ← 种子条目 {item.primary_seed.qid} 人工指定")
    else:
        stage_hit = _first_match(taxonomy.stage_rules, corpus)
        if stage_hit is not None:
            rule, keyword = stage_hit
            stage = rule.target
            reasons.append(f"stage={stage} ← 关键词「{keyword}」命中规则：{rule.reason}")
        else:
            stage = taxonomy.defaults.stage
            reasons.append(f"stage={stage} ← 无规则命中，取默认阶段")

    return Annotation(
        discipline=discipline,
        stage=stage,
        tradition=tradition,
        reasons=tuple(reasons),
    )


def build_draft(item: RawItem, annotation: Annotation, taxonomy: Taxonomy) -> NodeDraft:
    """由原始条目 + 标注生成一条待入库节点。"""
    title = item.title
    if title is None:  # pragma: no cover - 过滤阶段已保证有标题
        raise ValueError(f"条目 {item.qid} 没有可用标题")

    summary = item.summary
    if summary is None and taxonomy.filters.allow_en_summary and item.desc_en:
        summary = item.desc_en.strip() or None

    return NodeDraft(
        slug=wikidata_slug(item.qid),
        type=taxonomy.defaults.node_type,
        title=title,
        summary=summary,
        stage=annotation.stage,
        discipline=annotation.discipline,
        tradition=annotation.tradition,
        language=taxonomy.defaults.language,
        status=taxonomy.defaults.status,
        source_id=item.qid,
        source_url=item.wikipedia_url,
    )


def _first_match(rules: tuple[Rule, ...], corpus: str) -> tuple[Rule, str] | None:
    """返回第一条命中的规则及命中的关键词。"""
    for rule in rules:
        for keyword in rule.any:
            if keyword.casefold() in corpus:
                return (rule, keyword)
    return None
