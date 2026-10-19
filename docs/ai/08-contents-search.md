# 任务书 08 · 正文纳入搜索（contents → Meilisearch）

- **分支**：`kuoleroy/contents-search`
- **worktree**：`E:\wk\csearch`
- **波次**：**可立即起步**——06 已完工合并，`apps/api/app/services/**` 与搜索端点已释放
- **前置**：06 已把 `nodes` 索引进 Meilisearch；05 正在写 `contents` 正文（**数据后到**）

## 目标

让搜索**能搜到正文**：现在只索引 `title` / `summary`，05 产出的正文（`contents.body_ref` 的 MDX）搜不到。把正文纳入索引，命中后门户能显示正文片段。

## 独占文件

- `apps/api/app/services/**`、`apps/api/app/api/v1/search.py`
- `apps/web/app/search/**`

## 不要动

- `apps/api/app/api/v1/nodes.py` 等既有端点、`apps/api/app/core/**`（配置已存在，直接用）
- `apps/admin/**`、`apps/importer/**`、`docker-compose.yml`、骨架 JSON、主文档

## 步骤

> 环境：`node_modules` 与 `apps/api` 的 `.venv` 已由主控预装；**不要自己起 compose、不要抢端口**。

1. **取正文**：读 `contents` → 取 `body_ref` 为**能解出文本**的那些（MDX 字符串 / 文件 UUID / `http(s)` 链接，见 13.8），转**纯文本**；取不到文本的**跳过不报错**。
2. **扩索引**：节点文档加 `bodyText` 字段；`searchableAttributes` 扩为 `[title, summary, bodyText]`。settings 仍在 `app/services/meilisearch_client.py` **单点定义**（重建自动对齐）。
3. **端点不变**：`/v1/search` 的 `q` / `limit` / `discipline` / `stage` / `tradition` 与统一信封 `{success,data,meta,error}` 保持不变；`meta` 字段不破坏现有前端。
4. **门户**：`/search` 结果卡补正文片段（可选浅高亮）；沿用 `safe()` 降级。
5. **降级不变**：Meilisearch 不可达**恒 HTTP 200 + `degraded=true`**。

## 验收标准

- `docker compose exec api python -m app.services.reindex --reset` 成功；`GET /v1/search?q=<正文中的词>` 命中且 `total>0`
- `contents` 为空 / 正文不可解时**不报错**（`bodyText` 缺省省略）
- `pnpm --filter web build` 通过；`/search?q=` 页面可用
- 既有端点零改动；**停掉 Meilisearch 仍 200 degraded**

## 注意

- 复用现有 `meilisearch` SDK 与 `app/services/`（`indexer.py` / `search.py` / `meilisearch_client.py`），**不新造轮子**
- 正文数据由 05 提供——**主控在 05 合并后重跑 `reindex`**，本任务才真正生效；代码先行，验收分两段做
- 新增依赖须 MIT/Apache-2.0；预计**不需要新增依赖**
