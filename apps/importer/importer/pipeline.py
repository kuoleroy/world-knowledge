"""编排：抓取 → 合并 → 过滤 → 标注 → 落盘。

一次运行产出一个学科目录：

    out/<discipline>/
      nodes.jsonl        待写入 nodes 表的记录（列名与表结构一致，可直接推 Directus）
      annotations.jsonl  每条标注的依据（走哪条规则、命中哪个词），供人工复核
      wiki/<slug>.json   Wikipedia 摘要素材（CC BY-SA，改写用，不直接入库）
      summary.json       本次运行的参数、统计与文件清单

选取策略：先按传统分组，再轮转取样。原因是门户把各知识传统**平级并列**，
不能让站点链接数最高的「疾病 / 医学」一堆实证条目把其他传统挤没。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .annotate import annotate, build_draft
from .config import AppConfig
from .models import Annotation, NodeDraft, RawItem
from .net import FetchError, Fetcher
from .output import ensure_dir, write_json, write_jsonl
from .sources import wikidata, wikipedia


@dataclass(frozen=True)
class RunOptions:
    """一次导入的运行参数。"""

    discipline: str
    limit: int = 60
    with_wikipedia: bool = True
    out_dir: Path | None = None


@dataclass
class RunResult:
    """运行结果，供命令行打印。"""

    discipline: str
    out_dir: Path
    nodes_path: Path
    annotations_path: Path
    summary_path: Path
    nodes: list[NodeDraft]
    by_stage: dict[str, int]
    by_tradition: dict[str, int]
    skipped: dict[str, int]
    wiki_documents: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Selected:
    """一条入选条目及其标注。"""

    item: RawItem
    annotation: Annotation


def run(config: AppConfig, fetcher: Fetcher, options: RunOptions) -> RunResult:
    """按学科计划跑一次完整导入（只落盘，不写库）。"""
    if options.limit <= 0:
        raise ValueError("--limit 必须大于 0")

    plan = config.taxonomy.plan(options.discipline)
    if len(plan.seeds) > config.network.max_seeds_per_run:
        raise ValueError(
            f"本学科有 {len(plan.seeds)} 个种子，超过 max_seeds_per_run="
            f"{config.network.max_seeds_per_run}；请拆分计划或调整上限"
        )

    # 1. 抓取并合并：同一 QID 可能被多个种子命中
    merged: dict[str, RawItem] = {}
    warnings: list[str] = []
    skipped: Counter[str] = Counter()
    for seed in plan.seeds:
        try:
            fetched = wikidata.fetch_seed(fetcher, config.sources, seed, config.taxonomy.filters)
        except FetchError as exc:
            # 单个种子失败不该拖垮整条导入线
            skipped["seed_failed"] += 1
            warnings.append(f"种子 {seed.qid} 抓取失败，已跳过：{exc}")
            continue
        for item in fetched:
            existing = merged.get(item.qid)
            if existing is None:
                merged[item.qid] = item
            else:
                existing.seed_qids |= item.seed_qids

    # 2. 全局过滤 + 每个种子的上限（跳过原因逐条记账，便于调规则）
    candidates: list[RawItem] = []
    per_seed: Counter[str] = Counter()
    for item in merged.values():
        reason = _reject_reason(item, config, plan.exclude_qids)
        if reason is not None:
            skipped[reason] += 1
            continue
        if per_seed[item.primary_seed.qid] >= item.primary_seed.limit:
            skipped["seed_limit"] += 1
            continue
        per_seed[item.primary_seed.qid] += 1
        candidates.append(item)

    # 3. 标注 + 按传统轮转取样
    annotated = [_Selected(item=item, annotation=annotate(item, config.taxonomy)) for item in candidates]
    selected = _select_round_robin(
        annotated,
        stage_order=config.skeleton.stages,
        tradition_order=config.skeleton.traditions,
        limit=options.limit,
    )
    skipped["over_limit"] += max(0, len(annotated) - len(selected))

    drafts = [
        (entry.item, entry.annotation, build_draft(entry.item, entry.annotation, config.taxonomy))
        for entry in selected
    ]

    # 4. 落盘
    out_dir = ensure_dir((options.out_dir or (config.app_dir / "out")) / options.discipline)
    nodes_path = out_dir / "nodes.jsonl"
    annotations_path = out_dir / "annotations.jsonl"
    summary_path = out_dir / "summary.json"
    wiki_dir = ensure_dir(out_dir / "wiki")

    write_jsonl(nodes_path, [draft.to_row() for _, _, draft in drafts])
    write_jsonl(
        annotations_path,
        [
            _annotation_row(item, annotation, draft)
            for item, annotation, draft in drafts
        ],
    )

    wiki_documents = 0
    if options.with_wikipedia:
        for item, _, draft in drafts:
            if _write_wiki_summary(fetcher, config, wiki_dir, item, draft):
                wiki_documents += 1
        # 清掉上一次运行留下的、本次已不在结果里的素材文件，保证目录 = 本次运行结果
        current_slugs = {draft.slug for _, _, draft in drafts}
        for stale in wiki_dir.glob("*.json"):
            if stale.stem not in current_slugs:
                stale.unlink()

    by_stage = _count(draft.stage for _, _, draft in drafts)
    by_tradition = _count(draft.tradition for _, _, draft in drafts)

    write_json(
        summary_path,
        {
            "generated_at": _now(),
            "discipline": options.discipline,
            "discipline_name_zh": config.skeleton.disciplines.get(options.discipline),
            "slug_rule": "wd-<QID>（如 wd-Q12345）",
            "limit": options.limit,
            "with_wikipedia": options.with_wikipedia,
            "total": len(drafts),
            "by_stage": by_stage,
            "by_tradition": by_tradition,
            "wiki_documents": wiki_documents,
            "skipped": dict(sorted(skipped.items())),
            "warnings": warnings,
            "seed_count": len(plan.seeds),
            "seeds": [
                {
                    "qid": seed.qid,
                    "expect_zh": seed.expect_zh,
                    "tradition": seed.tradition,
                    "stage": seed.stage,
                    "limit": seed.limit,
                    "min_sitelinks": seed.min_sitelinks,
                }
                for seed in plan.seeds
            ],
            "files": {
                "nodes": nodes_path.name,
                "annotations": annotations_path.name,
                "wiki_dir": wiki_dir.name,
                "summary": summary_path.name,
            },
            "notes": [
                "nodes.jsonl 只含 nodes 表字段，可直接 upsert 到 Directus /items/nodes",
                "summary 取自 Wikidata 描述（CC0），无署名义务",
                "wiki/*.json 为 CC BY-SA 4.0 改写素材，发布前须署名，勿直接搬运",
            ],
        },
    )

    return RunResult(
        discipline=options.discipline,
        out_dir=out_dir,
        nodes_path=nodes_path,
        annotations_path=annotations_path,
        summary_path=summary_path,
        nodes=[draft for _, _, draft in drafts],
        by_stage=by_stage,
        by_tradition=by_tradition,
        skipped=dict(sorted(skipped.items())),
        wiki_documents=wiki_documents,
        warnings=tuple(warnings),
    )


def _reject_reason(item: RawItem, config: AppConfig, excluded: Mapping[str, str]) -> str | None:
    # 跨学科重复：该 QID 归「保留方」学科，本学科显式排除（见 taxonomy 的 exclude_qids）
    if item.qid in excluded:
        return "excluded_by_discipline"
    filters = config.taxonomy.filters
    if item.qid in filters.exclude_qids:
        return "excluded_by_config"
    if item.sitelinks < filters.min_sitelinks:
        return "low_sitelinks"
    if filters.require_zh_label and not item.label_zh:
        return "no_zh_label"
    if filters.require_zh_sitelink and not item.zhwiki_url:
        return "no_zh_sitelink"
    if not item.title:
        return "no_title"
    return None


def _select_round_robin(
    entries: list[_Selected],
    *,
    stage_order: tuple[str, ...],
    tradition_order: tuple[str, ...],
    limit: int,
) -> list[_Selected]:
    """按「阶段 × 传统」双维度轮转取样，保证每个导航页面都有内容。

    门户是「阶段 × 学科」导航，节点还带传统标签；只按单一维度取样会让某些阶段/传统
    （例如研究阶段、信仰传统）被站点链接数高的大类挤空。
    """
    stage_rank = {stage: rank for rank, stage in enumerate(stage_order)}
    tradition_rank = {tradition: rank for rank, tradition in enumerate(tradition_order)}

    buckets: dict[tuple[int, int], list[_Selected]] = {}
    for entry in sorted(entries, key=lambda e: (-e.item.sitelinks, e.item.qid)):
        key = (
            stage_rank.get(entry.annotation.stage, len(stage_rank)),
            tradition_rank.get(entry.annotation.tradition, len(tradition_rank)),
        )
        buckets.setdefault(key, []).append(entry)

    ordered = [buckets[key] for key in sorted(buckets)]
    picked: list[_Selected] = []
    depth = 0
    while len(picked) < limit:
        added = False
        for bucket in ordered:
            if depth < len(bucket):
                picked.append(bucket[depth])
                added = True
                if len(picked) >= limit:
                    break
        if not added:
            break
        depth += 1

    return sorted(
        picked,
        key=lambda e: (
            stage_rank.get(e.annotation.stage, len(stage_rank)),
            tradition_rank.get(e.annotation.tradition, len(tradition_rank)),
            -e.item.sitelinks,
            e.item.qid,
        ),
    )


def _annotation_row(item: RawItem, annotation: Annotation, draft: NodeDraft) -> dict[str, Any]:
    return {
        "slug": draft.slug,
        "source_id": item.qid,
        "title": draft.title,
        "stage": draft.stage,
        "discipline": draft.discipline,
        "tradition": draft.tradition,
        "reasons": list(annotation.reasons),
        "primary_seed": item.primary_seed.qid,
        "seed_qids": sorted(item.seed_qids),
        "sitelinks": item.sitelinks,
        "label_en": item.label_en,
        "desc_en": item.desc_en,
        "zhwiki_url": item.zhwiki_url,
        "enwiki_url": item.enwiki_url,
        "has_summary": draft.summary is not None,
    }


def _write_wiki_summary(
    fetcher: Fetcher,
    config: AppConfig,
    wiki_dir: Path,
    item: RawItem,
    draft: NodeDraft,
) -> bool:
    """落一条维基摘要素材；拿不到就跳过（不影响节点入库）。"""
    lang: str | None = None
    url: str | None = None
    for candidate_lang in config.sources.wikipedia_languages:
        if candidate_lang == "zh" and item.zhwiki_url:
            lang, url = "zh", item.zhwiki_url
            break
        if candidate_lang == "en" and item.enwiki_url:
            lang, url = "en", item.enwiki_url
            break
    if lang is None or url is None:
        return False

    title = wikipedia.title_from_url(url)
    if not title:
        return False
    summary = wikipedia.fetch_summary(fetcher, config.sources, lang=lang, title=title)
    if summary is None:
        return False
    write_json(wiki_dir / f"{draft.slug}.json", summary.to_json())
    return True


def _count(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
