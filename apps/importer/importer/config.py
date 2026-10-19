"""配置文件加载与校验。

两个文件：
- ``config/sources.yaml``：端点、User-Agent、代理、限流
- ``config/taxonomy.yaml``：stage / tradition 关键词规则 + 学科种子

校验的硬约束：所有 stage / discipline / tradition id 必须存在于骨架 JSON，
否则直接抛 :class:`ConfigError`，不产出脏数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

import yaml

from .models import QID_PATTERN, Seed
from .skeleton import Skeleton

CONFIG_DIRNAME = "config"
SOURCES_FILENAME = "sources.yaml"
TAXONOMY_FILENAME = "taxonomy.yaml"


class ConfigError(ValueError):
    """配置缺失、格式错误或引用了不存在的骨架 id。"""


@dataclass(frozen=True)
class NetworkConfig:
    """网络参数。"""

    user_agent: str
    timeout_seconds: float
    retries: int
    min_interval_seconds: float
    proxy: str | None
    max_seeds_per_run: int


@dataclass(frozen=True)
class SourcesConfig:
    """数据源端点与许可信息。"""

    sparql_endpoint: str
    entity_api: str
    label_languages: str
    wikipedia_endpoint: str
    wikipedia_languages: tuple[str, ...]
    wikipedia_license: str
    wikipedia_attribution: str


@dataclass(frozen=True)
class Filters:
    """抓取质量过滤。"""

    min_sitelinks: int
    require_zh_label: bool
    require_zh_sitelink: bool
    allow_en_summary: bool
    exclude_qids: Mapping[str, str]


@dataclass(frozen=True)
class Defaults:
    """产出字段默认值（键名与 nodes 表一致）。"""

    language: str
    node_type: str
    status: str
    stage: str


@dataclass(frozen=True)
class Rule:
    """一条关键词规则：命中 ``any`` 中任一词则把目标字段设为 ``target``。"""

    target: str
    any: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class DisciplinePlan:
    """一个学科的导入计划。

    ``exclude_qids``：本学科**不得产出**的条目（QID → 归属理由）。用于处理跨学科重复——
    同一 QID 可能同时从两个学科的种子子树里被继承到，但节点只有一个 discipline 字段，
    后写会覆盖。这些 QID 一律归「保留方」学科，落选学科在这里显式排除，保证归属稳定。
    """

    discipline: str
    note: str
    seeds: tuple[Seed, ...]
    exclude_qids: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Taxonomy:
    """taxonomy.yaml 的完整内容。"""

    defaults: Defaults
    filters: Filters
    stage_rules: tuple[Rule, ...]
    tradition_rules: tuple[Rule, ...]
    plans: dict[str, DisciplinePlan]

    def plan(self, discipline: str) -> DisciplinePlan:
        try:
            return self.plans[discipline]
        except KeyError:
            available = ", ".join(sorted(self.plans)) or "（无）"
            raise ConfigError(
                f"taxonomy.yaml 里没有学科 {discipline!r} 的导入计划；已有：{available}"
            ) from None


@dataclass(frozen=True)
class AppConfig:
    """一次运行所需的全部配置。"""

    app_dir: Path
    network: NetworkConfig
    sources: SourcesConfig
    taxonomy: Taxonomy
    skeleton: Skeleton

    def with_overrides(self, *, proxy: str | None = None) -> "AppConfig":
        """命令行覆盖代理；``None`` 表示不改。"""
        if proxy is None:
            return self
        return replace(self, network=replace(self.network, proxy=proxy))


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"配置文件缺失：{path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"配置文件 YAML 解析失败：{path}\n{exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"配置文件顶层应为映射：{path}")
    return payload


def _mapping(payload: Mapping[str, Any], key: str, *, where: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ConfigError(f"{where} 缺少映射字段 {key!r}")
    return value


def _string(payload: Mapping[str, Any], key: str, *, where: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} 字段 {key!r} 必须是非空字符串")
    return value.strip()


def _integer(payload: Mapping[str, Any], key: str, *, where: str, default: int | None = None) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{where} 字段 {key!r} 必须是整数")
    return value


def _number(payload: Mapping[str, Any], key: str, *, where: str, default: float | None = None) -> float:
    value = payload.get(key, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{where} 字段 {key!r} 必须是数字")
    return float(value)


def _boolean(payload: Mapping[str, Any], key: str, *, where: str, default: bool | None = None) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{where} 字段 {key!r} 必须是 true/false")
    return value


def _string_list(payload: Mapping[str, Any], key: str, *, where: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{where} 字段 {key!r} 必须是非空数组")
    items: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise ConfigError(f"{where} 字段 {key!r} 的元素必须是非空字符串")
        items.append(entry.strip())
    return tuple(items)


def load_sources(path: Path) -> tuple[NetworkConfig, SourcesConfig]:
    """解析 sources.yaml。"""
    payload = _read_yaml(path)
    network = _mapping(payload, "network", where=str(path))
    sources = _mapping(payload, "sources", where=str(path))
    wikidata = _mapping(sources, "wikidata", where=f"{path}:sources")
    wikipedia = _mapping(sources, "wikipedia", where=f"{path}:sources")

    proxy = network.get("proxy")
    if proxy is not None and (not isinstance(proxy, str) or not proxy.strip()):
        raise ConfigError(f"{path}:network.proxy 必须是字符串或 null")

    return (
        NetworkConfig(
            user_agent=_string(network, "user_agent", where=f"{path}:network"),
            timeout_seconds=_number(network, "timeout_seconds", where=f"{path}:network"),
            retries=_integer(network, "retries", where=f"{path}:network"),
            min_interval_seconds=_number(network, "min_interval_seconds", where=f"{path}:network"),
            proxy=proxy.strip() if isinstance(proxy, str) else None,
            max_seeds_per_run=_integer(network, "max_seeds_per_run", where=f"{path}:network"),
        ),
        SourcesConfig(
            sparql_endpoint=_string(wikidata, "sparql_endpoint", where=f"{path}:wikidata"),
            entity_api=_string(wikidata, "entity_api", where=f"{path}:wikidata"),
            label_languages=_string(wikidata, "label_languages", where=f"{path}:wikidata"),
            wikipedia_endpoint=_string(wikipedia, "summary_endpoint", where=f"{path}:wikipedia"),
            wikipedia_languages=_string_list(wikipedia, "languages", where=f"{path}:wikipedia"),
            wikipedia_license=_string(wikipedia, "license", where=f"{path}:wikipedia"),
            wikipedia_attribution=_string(wikipedia, "attribution", where=f"{path}:wikipedia"),
        ),
    )


def _parse_rules(
    payload: Mapping[str, Any], key: str, *, target_field: str, where: str
) -> tuple[Rule, ...]:
    raw = payload.get(key, [])
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ConfigError(f"{where} 字段 {key!r} 必须是数组")
    rules: list[Rule] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            raise ConfigError(f"{where} 字段 {key}[{index}] 必须是映射")
        rules.append(
            Rule(
                target=_string(entry, target_field, where=f"{where}:{key}[{index}]"),
                any=_string_list(entry, "any", where=f"{where}:{key}[{index}]"),
                reason=str(entry.get("reason") or "").strip(),
            )
        )
    return tuple(rules)


def _parse_seed(entry: Mapping[str, Any], *, discipline: str, where: str) -> Seed:
    qid = _string(entry, "qid", where=where)
    if not QID_PATTERN.match(qid):
        raise ConfigError(f"{where} 的 qid 不合法：{qid!r}（应形如 Q12345）")
    stage = entry.get("stage")
    if stage is not None and (not isinstance(stage, str) or not stage.strip()):
        raise ConfigError(f"{where} 的 stage 必须是非空字符串或省略")
    return Seed(
        qid=qid,
        discipline=discipline,
        tradition=_string(entry, "tradition", where=where),
        expect_zh=str(entry.get("expect_zh") or "").strip(),
        stage=stage.strip() if isinstance(stage, str) else None,
        limit=_integer(entry, "limit", where=where, default=5),
        min_sitelinks=(
            _integer(entry, "min_sitelinks", where=where)
            if "min_sitelinks" in entry
            else None
        ),
        include_subclasses=(
            _boolean(entry, "include_subclasses", where=where)
            if "include_subclasses" in entry
            else False
        ),
        note=str(entry.get("note") or "").strip(),
    )


def load_taxonomy(path: Path, skeleton: Skeleton) -> Taxonomy:
    """解析并校验 taxonomy.yaml。"""
    payload = _read_yaml(path)
    where = str(path)

    defaults_raw = _mapping(payload, "defaults", where=where)
    filters_raw = _mapping(payload, "filters", where=where)
    exclude_raw = filters_raw.get("exclude_qids") or {}
    if not isinstance(exclude_raw, Mapping):
        raise ConfigError(f"{where}:filters.exclude_qids 必须是映射（QID → 理由）")

    defaults = Defaults(
        language=_string(defaults_raw, "language", where=f"{where}:defaults"),
        node_type=_string(defaults_raw, "node_type", where=f"{where}:defaults"),
        status=_string(defaults_raw, "status", where=f"{where}:defaults"),
        stage=_string(defaults_raw, "stage", where=f"{where}:defaults"),
    )
    filters = Filters(
        min_sitelinks=_integer(filters_raw, "min_sitelinks", where=f"{where}:filters"),
        require_zh_label=_boolean(filters_raw, "require_zh_label", where=f"{where}:filters"),
        require_zh_sitelink=_boolean(filters_raw, "require_zh_sitelink", where=f"{where}:filters"),
        allow_en_summary=_boolean(filters_raw, "allow_en_summary", where=f"{where}:filters"),
        exclude_qids={str(key): str(value) for key, value in exclude_raw.items()},
    )
    stage_rules = _parse_rules(payload, "stage_rules", target_field="stage", where=where)
    tradition_rules = _parse_rules(
        payload, "tradition_rules", target_field="tradition", where=where
    )

    disciplines_raw = _mapping(payload, "disciplines", where=where)
    plans: dict[str, DisciplinePlan] = {}
    for discipline, entry in disciplines_raw.items():
        if not isinstance(entry, Mapping):
            raise ConfigError(f"{where}:disciplines.{discipline} 必须是映射")
        exclude_raw = entry.get("exclude_qids") or {}
        if not isinstance(exclude_raw, Mapping):
            raise ConfigError(f"{where}:disciplines.{discipline}.exclude_qids 必须是映射（QID → 理由）")
        seed_entries = entry.get("seeds")
        if not isinstance(seed_entries, list) or not seed_entries:
            raise ConfigError(f"{where}:disciplines.{discipline}.seeds 必须是非空数组")
        seeds = tuple(
            _parse_seed(
                seed,
                discipline=str(discipline),
                where=f"{where}:disciplines.{discipline}.seeds[{index}]",
            )
            for index, seed in enumerate(seed_entries)
            if isinstance(seed, Mapping)
        )
        if len(seeds) != len(seed_entries):
            raise ConfigError(f"{where}:disciplines.{discipline}.seeds 的元素必须是映射")
        plans[str(discipline)] = DisciplinePlan(
            discipline=str(discipline),
            note=str(entry.get("note") or "").strip(),
            seeds=seeds,
            exclude_qids={str(key): str(value) for key, value in exclude_raw.items()},
        )

    taxonomy = Taxonomy(
        defaults=defaults,
        filters=filters,
        stage_rules=stage_rules,
        tradition_rules=tradition_rules,
        plans=plans,
    )
    validate_taxonomy(taxonomy, skeleton)
    return taxonomy


def validate_taxonomy(taxonomy: Taxonomy, skeleton: Skeleton) -> None:
    """交叉校验 taxonomy 与骨架定义。"""
    problems: list[str] = []

    if not skeleton.has_stage(taxonomy.defaults.stage):
        problems.append(f"defaults.stage={taxonomy.defaults.stage!r} 不在骨架阶段里")

    for index, rule in enumerate(taxonomy.stage_rules):
        if not skeleton.has_stage(rule.target):
            problems.append(f"stage_rules[{index}] 的 stage={rule.target!r} 不在骨架阶段里")

    for index, rule in enumerate(taxonomy.tradition_rules):
        if not skeleton.has_tradition(rule.target):
            problems.append(
                f"tradition_rules[{index}] 的 tradition={rule.target!r} 不在骨架传统里"
            )

    if not taxonomy.plans:
        problems.append("disciplines 下没有任何导入计划")

    for discipline, plan in taxonomy.plans.items():
        if not skeleton.has_discipline(discipline):
            problems.append(f"学科 {discipline!r} 不在骨架学科里")
        seen: set[str] = set()
        for seed in plan.seeds:
            if seed.discipline != discipline:
                problems.append(
                    f"{discipline}: 种子 {seed.qid} 的 discipline={seed.discipline!r} 与所属计划不一致"
                )
            if not skeleton.has_tradition(seed.tradition):
                problems.append(f"{discipline}: 种子 {seed.qid} 的 tradition={seed.tradition!r} 不合法")
            if seed.stage is not None and not skeleton.has_stage(seed.stage):
                problems.append(f"{discipline}: 种子 {seed.qid} 的 stage={seed.stage!r} 不合法")
            if seed.limit <= 0:
                problems.append(f"{discipline}: 种子 {seed.qid} 的 limit 必须大于 0")
            if seed.qid in seen:
                problems.append(f"{discipline}: 种子 {seed.qid} 重复出现")
            seen.add(seed.qid)
        for qid in plan.exclude_qids:
            if not QID_PATTERN.match(qid):
                problems.append(f"{discipline}: exclude_qids 里的 {qid!r} 不是合法 QID")

    if problems:
        raise ConfigError("配置校验失败：\n  - " + "\n  - ".join(problems))


def load_config(app_dir: Path, skeleton: Skeleton) -> AppConfig:
    """读取 ``<app_dir>/config`` 下的两个 YAML 并完成校验。"""
    config_dir = app_dir / CONFIG_DIRNAME
    network, sources = load_sources(config_dir / SOURCES_FILENAME)
    taxonomy = load_taxonomy(config_dir / TAXONOMY_FILENAME, skeleton)
    return AppConfig(
        app_dir=app_dir,
        network=network,
        sources=sources,
        taxonomy=taxonomy,
        skeleton=skeleton,
    )
