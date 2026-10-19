# 任务书 07 · 多学科内容扩展（种子整理）

- **分支**：`kuoleroy/multi-discipline`
- **worktree**：`E:\wk\multi`
- **波次**：**阶段一可立即起步**（只动 `apps/importer/config/**`，与 05 的文件不重叠）；**阶段二（跑数 / 落库）等 05 合并**
- **前置**：03 已跑通 `health_medicine`（60 条）；骨架 JSON 冻结；05 正占用 `apps/importer` 的其余部分

## 目标

门户现在**只有 1 个学科有内容**（12 学科里其余 11 个是空的）。本任务：为其余 11 个学科补齐**种子条目映射**，让 runner 一条命令就能把每个学科的内容产出来。

## 独占文件

- `apps/importer/config/**`（`taxonomy.yaml`；`sources.yaml` 如需微调）

## 不要动

- `apps/importer/importer/**`、`apps/importer/out/**`（**05 在用**）
- `apps/api/**`、`apps/web/**`、`apps/admin/**`、`docker-compose.yml`、骨架 JSON、主文档

## 步骤（阶段一 · 可立即）

1. 读现有 `config/taxonomy.yaml` 里 `health_medicine` 的范式（`seeds:` 人工挑 QID + `tradition` / `stage` / `limit` / `min_sitelinks`）。
2. 为其余 11 学科各补 `seeds`：
   - `language_communication`、`thinking_humanities`、`education_development`、`society_governance`、`economy_business`、`math_natural_sciences`、`information_computing`、`engineering_construction`、`agriculture_food`、`defense_security`、`life_experience`
   - 每学科 **≥8 个种子**，覆盖该学科主线；**5 个 `tradition` 在 12 学科整体上有覆盖**即可（不要求每学科全覆盖）
   - 遵守 `filters`（`require_zh_label` / `require_zh_sitelink` / `min_sitelinks`），种子中文标签**人工核对**；不确定的 QID 宁可少放
   - 概念型种子可开 `include_subclasses`（参考 Q200253 中医学的写法）
3. 跑 `python -m importer check --online`（国内网络带 `--proxy http://127.0.0.1:7890`）验证配置与骨架一致、QID 中文标签不漂移。

## 步骤（阶段二 · 等 05 合并进 main 后）

4. **主控**先起新栈、按学科逐个 `run` + `push`（或在本分支续做，**由主控裁定**）。
5. 每学科 nodes 落库后，**主控重跑 `docker compose exec api python -m app.services.reindex`** 让搜索覆盖。

## 验收标准（阶段一）

- `python -m importer check --online` 全绿（12 学科 `seeds` 全部可解析、中文标签无漂移）
- `taxonomy.yaml` 的 `disciplines` 覆盖 **12 个学科 id**，取值全部来自骨架 JSON，**不新增枚举**
- 未触碰 `apps/importer/importer/**` 与 `out/**`

## 注意

- 学科 id 必须来自 `apps/api/app/data/skeleton/*.json`（冻结契约），写错会加载即报错
- 种子是**人工挑选**，不靠关键词猜；本任务的真正工作量在「挑得准、覆盖得全」
- 阶段二跑数由主控执行，分支**不要自己起 compose、不要抢端口**
