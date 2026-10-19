# 任务书 03 · 开放知识库内容导入

- **分支**：`kuoleroy/content-import`
- **worktree**：`E:\wk\importer`
- **波次**：**可立即起步（代码先行）**——抓取与标注现在就能写；仅「落库」步骤等 01
- **前置**：环境已由人类预装（Python venv：`E:\wk\importer\.venv`）；`nodes` 表由 01 提供，**落库前**需等其合并进 `main`

## 目标

不自己从零编内容：从**开放知识库**抓条目，按 `stage × discipline × tradition` 标注，写入 `nodes` 表（来源与链接一并落库）。

## 独占文件

- `apps/importer/**`（新建整个目录）
- `scripts/**`（如需要放辅助脚本）

## 不要动

- `apps/api/**`、`apps/web/**`、`apps/admin/**`
- `docker-compose.yml`
- `packages/types/index.ts`、skeleton JSON、主文档
- **骨架定义**：阶段/学科/传统 id 一律用 skeleton JSON 里的值，不许自造

## 步骤

> 步骤 1-3、6 **现在即可做**；步骤 4（写入库）**等 01 合并后再做**。

1. **选来源**（先做前两个）：
   - `Wikidata` —— 结构化、有稳定 QID，作为主键来源
   - `Wikipedia` —— 正文摘要，作为改写/翻译素材（**注意许可与署名**）
   - （可选后加）`OpenAlex` —— 学术条目
2. **写抓取**：`apps/importer/` 下建 Python 包，用 `httpx` 或 `requests`；产出条目清单（JSON）。
3. **写标注**：把条目映射到 4 阶段 × 12 学科 × 5 传统，规则放在**可读的配置文件**里（如 YAML），便于人工校正。
4. **写入库**（二选一，总结里说明理由）：
   - 走 Directus `/items/nodes` REST（需管理员 token）
   - 直连 MySQL
   均需 **upsert 幂等**（以 `slug` / `source_id` 为键，重复跑不重复插）。
5. **先跑通一个学科线**（建议 `health_medicine`，传统差异最典型），验证后再扩。
6. **写运行说明**：一条命令跑一次导入。

## 验收标准

- 跑一次导入后，`nodes` 表出现带 `stage` / `discipline` / `tradition` / `source_id` / `source_url` 的记录
- 门户 `/stage/<stage>/<discipline>` 能列出这些节点
- 重复跑不产生重复行（幂等）

## 交付契约

总结里写清：**slug 生成规则**（如 `wd-Q12345`）、**来源许可/署名要求**、以及你选的写入方式。
