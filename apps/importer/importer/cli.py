"""命令行入口：一条命令跑一次导入。

    python -m importer run   --discipline health_medicine      # 抓取 + 标注 + 落盘
    python -m importer check [--online]                        # 校验配置与骨架一致性
    python -m importer push  --discipline health_medicine      # 写入库（等主控通知后再跑）
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .config import AppConfig, ConfigError, load_config
from .net import FetchError, Fetcher
from .output import read_jsonl
from .pipeline import RunOptions, RunResult, run
from .skeleton import SkeletonError, find_repo_root, load_skeleton
from .verify import run as verify_run
from .writers.directus import BASE_URL_ENV, DEFAULT_BASE_URL, TOKEN_ENV, DirectusError, DirectusWriter

# ``apps/importer``；配置与产出都相对它定位
APP_DIR = Path(__file__).resolve().parent.parent
CACHE_DIRNAME = ".cache"


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="python -m importer",
        description="开放知识库内容导入：Wikidata 抓条目 → 按阶段×学科×传统标注 → 产出 nodes JSONL",
    )
    parser.add_argument("--version", action="version", version=f"importer {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="抓取 + 标注 + 落盘（不写库）")
    run_parser.add_argument("--discipline", required=True, help="学科 id，如 health_medicine")
    run_parser.add_argument("--limit", type=int, default=60, help="最多产出多少条节点（默认 60）")
    run_parser.add_argument("--proxy", default=None, help="HTTP(S) 代理，如 http://127.0.0.1:7890")
    run_parser.add_argument("--no-wiki", action="store_true", help="不抓维基摘要（改写素材）")
    run_parser.add_argument("--refresh", action="store_true", help="忽略本地缓存，强制重新请求")
    run_parser.add_argument("--out", default=None, help="产出目录（默认 apps/importer/out）")

    check_parser = subparsers.add_parser("check", help="校验配置、骨架 id 与种子标签")
    check_parser.add_argument("--online", action="store_true", help="联网核对种子 QID 的中文标签")
    check_parser.add_argument("--proxy", default=None, help="HTTP(S) 代理")
    check_parser.add_argument("--refresh", action="store_true", help="忽略本地缓存")

    push_parser = subparsers.add_parser("push", help="把 nodes.jsonl 幂等写入 Directus（步骤 4）")
    push_parser.add_argument("--discipline", required=True, help="学科 id，如 health_medicine")
    push_parser.add_argument("--yes", action="store_true", help="真的写库；不加则只做 dry-run")
    push_parser.add_argument("--base-url", default=None, help="Directus 地址（默认 $DIRECTUS_URL）")
    push_parser.add_argument("--token", default=None, help="Directus 管理员 token（默认 $DIRECTUS_TOKEN）")
    push_parser.add_argument("--data-dir", default=None, help="nodes.jsonl 所在目录（默认 apps/importer/out）")

    verify_parser = subparsers.add_parser("verify", help="落库自检（只读）：条数/重复/空字段/内容指纹")
    verify_parser.add_argument("--discipline", required=True, help="学科 id，如 health_medicine")
    verify_parser.add_argument("--base-url", default=None, help="Directus 地址（默认 $DIRECTUS_URL）")
    verify_parser.add_argument(
        "--token", default=None, help="可选；public 只读即可，无需管理员 token"
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """入口；返回进程退出码。"""
    _configure_stdout()
    args = build_parser().parse_args(argv)

    try:
        config = _load_config(args)
        if args.command == "run":
            return _cmd_run(args, config)
        if args.command == "check":
            return _cmd_check(args, config)
        if args.command == "push":
            return _cmd_push(args, config)
        if args.command == "verify":
            return _cmd_verify(args, config)
    except (ConfigError, SkeletonError, FetchError, DirectusError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"未知命令：{args.command}", file=sys.stderr)  # pragma: no cover
    return 2


def _load_config(args: argparse.Namespace) -> AppConfig:
    app_dir = APP_DIR
    skeleton = load_skeleton(find_repo_root(app_dir))
    config = load_config(app_dir, skeleton)
    if getattr(args, "proxy", None):
        config = config.with_overrides(proxy=args.proxy)
    return config


def _cmd_run(args: argparse.Namespace, config: AppConfig) -> int:
    options = RunOptions(
        discipline=args.discipline,
        limit=args.limit,
        with_wikipedia=not args.no_wiki,
        out_dir=Path(args.out) if args.out else None,
    )
    with _make_fetcher(config, refresh=args.refresh) as fetcher:
        result = run(config, fetcher, options)

    _print_run_result(result, config)
    if not result.nodes:
        print("警告：没有产出任何节点，请检查过滤条件、代理与 seeds 配置", file=sys.stderr)
        return 1
    return 0


def _cmd_check(args: argparse.Namespace, config: AppConfig) -> int:
    skeleton = config.skeleton
    taxonomy = config.taxonomy
    print("骨架定义（只读）")
    print(f"  阶段  ：{', '.join(skeleton.stages)}")
    print(f"  学科  ：{len(skeleton.disciplines)} 个 —— {', '.join(skeleton.disciplines)}")
    print(f"  传统  ：{', '.join(skeleton.traditions)}")
    print("导入计划")
    for discipline, plan in taxonomy.plans.items():
        name = skeleton.disciplines.get(discipline, discipline)
        print(f"  {discipline}（{name}）：{len(plan.seeds)} 个种子")
    print(f"规则：阶段 {len(taxonomy.stage_rules)} 条 / 传统 {len(taxonomy.tradition_rules)} 条")
    print(f"过滤：min_sitelinks={taxonomy.filters.min_sitelinks}, "
          f"require_zh_label={taxonomy.filters.require_zh_label}, "
          f"require_zh_sitelink={taxonomy.filters.require_zh_sitelink}, "
          f"黑名单 {len(taxonomy.filters.exclude_qids)} 条")
    print("配置校验：通过（id 全部来自骨架 JSON）")

    if not args.online:
        print("提示：加 --online 可联网核对种子 QID 的中文标签是否漂移")
        return 0

    with _make_fetcher(config, refresh=args.refresh) as fetcher:
        warnings = _verify_seed_labels(config, fetcher)

    if warnings:
        print(f"种子标签核对：{len(warnings)} 条需人工确认")
        for warning in warnings:
            print(f"  - {warning}")
        return 0

    print("种子标签核对：全部一致")
    return 0


def _cmd_push(args: argparse.Namespace, config: AppConfig) -> int:
    data_dir = Path(args.data_dir) if args.data_dir else (config.app_dir / "out")
    nodes_path = data_dir / args.discipline / "nodes.jsonl"
    if not nodes_path.is_file():
        raise ValueError(f"找不到 {nodes_path}；先跑 run 生成待入库数据")

    rows = read_jsonl(nodes_path)
    if not rows:
        raise ValueError(f"{nodes_path} 是空的")

    with DirectusWriter.from_env(base_url=args.base_url, token=args.token) as writer:
        writer.ensure_collection()
        outcome = writer.upsert_many(rows, dry_run=not args.yes)

    mode = "写库" if args.yes else "dry-run（未写库，加 --yes 才真写）"
    print(f"[push] {args.discipline}：{len(rows)} 条，{mode}")
    print(f"  新建 {outcome.created} / 更新 {outcome.updated} / 无变化 {outcome.unchanged}")
    if outcome.failed:
        print(f"  失败 {len(outcome.failed)} 条：", file=sys.stderr)
        for slug, message in list(outcome.failed.items())[:10]:
            print(f"    {slug}: {message}", file=sys.stderr)
        return 1
    return 0


def _cmd_verify(args: argparse.Namespace, config: AppConfig) -> int:
    base_url = args.base_url or os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL)
    token = args.token or os.environ.get(TOKEN_ENV)
    report = verify_run(base_url, args.discipline, token=token)

    print(f"[verify] {args.discipline}：{report.total} 行（Directus {base_url}）")
    print(f"  重复 slug：{report.duplicate_slugs or '无'} / 重复 source_id：{report.duplicate_source_ids or '无'}")
    empty = "，".join(f"{name}={len(slugs)}" for name, slugs in report.missing.items())
    print(f"  必填字段空值：{empty}")
    print(f"  无 summary：{report.missing_summary}（上游无中文描述，待 04 改写补）")
    print(f"  阶段分布：{_format_counts(report.by_stage)}")
    print(f"  传统分布：{_format_counts(report.by_tradition)}")
    print(f"  内容指纹：{report.fingerprint}")

    if report.total == 0:
        print("结论：库里没有该学科的节点（先跑 run + push）", file=sys.stderr)
        return 1
    if not report.ok:
        print("结论：不一致（有重复或必填字段为空），请检查写入逻辑", file=sys.stderr)
        return 1
    print("结论：通过（无重复、必填字段齐全）")
    return 0


def _make_fetcher(config: AppConfig, *, refresh: bool) -> Fetcher:
    return Fetcher(
        config.network,
        cache_dir=config.app_dir / CACHE_DIRNAME,
        refresh=refresh,
    )


def _verify_seed_labels(config: AppConfig, fetcher: Fetcher) -> list[str]:
    """用 Wikidata 实体接口核对种子中文标签，发现 QID 漂移。"""
    seeds = [seed for plan in config.taxonomy.plans.values() for seed in plan.seeds]
    warnings: list[str] = []
    for start in range(0, len(seeds), 50):
        chunk = seeds[start : start + 50]
        payload = fetcher.get_json(
            config.sources.entity_api,
            params={
                "action": "wbgetentities",
                "ids": "|".join(seed.qid for seed in chunk),
                "props": "labels",
                "languages": "zh-hans|zh-cn|zh",
                "format": "json",
            },
        )
        entities = (payload or {}).get("entities")
        if not isinstance(entities, dict):
            warnings.append(f"实体接口返回异常，跳过第 {start + 1}-{start + len(chunk)} 个种子")
            continue
        for seed in chunk:
            entity = entities.get(seed.qid) or {}
            labels = entity.get("labels") if isinstance(entity, dict) else None
            label = _pick_zh_label(labels)
            if label is None:
                warnings.append(f"{seed.qid} 没有中文标签（配置 expect_zh={seed.expect_zh!r}）")
            elif seed.expect_zh and label != seed.expect_zh:
                warnings.append(
                    f"{seed.qid} 当前中文标签为 {label!r}，与配置 expect_zh={seed.expect_zh!r} "
                    "不一致（可能是简繁差异或 QID 漂移，需人工确认）"
                )
    return warnings


def _pick_zh_label(labels: Any) -> str | None:
    if not isinstance(labels, dict):
        return None
    for lang in ("zh-hans", "zh-cn", "zh"):
        entry = labels.get(lang)
        if isinstance(entry, dict):
            value = entry.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _print_run_result(result: RunResult, config: AppConfig) -> None:
    root = config.skeleton.root
    name = config.skeleton.disciplines.get(result.discipline, result.discipline)
    print(f"[run] 学科 {result.discipline}（{name}）")
    print(f"  产出节点：{len(result.nodes)} 条")
    print(f"  阶段分布：{_format_counts(result.by_stage)}")
    print(f"  传统分布：{_format_counts(result.by_tradition)}")
    print(f"  跳过统计：{_format_counts(result.skipped) if result.skipped else '无'}")
    print(f"  wiki 素材：{result.wiki_documents} 份")
    print(f"  nodes      ：{_relative(result.nodes_path, root)}")
    print(f"  annotations：{_relative(result.annotations_path, root)}")
    print(f"  summary    ：{_relative(result.summary_path, root)}")
    for warning in result.warnings:
        print(f"  警告：{warning}", file=sys.stderr)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "无"
    return "，".join(f"{key}={value}" for key, value in counts.items())


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _configure_stdout() -> None:
    """Windows 控制台按 UTF-8 输出，避免中文/符号乱码。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - 重定向到不支持的文件时
                pass


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
