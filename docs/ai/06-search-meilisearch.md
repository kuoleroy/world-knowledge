# 任务书 06 · 搜索（Meilisearch）

- **分支**：`kuoleroy/search-meilisearch`
- **worktree**：`E:\wk\search`
- **波次**：**可立即起步**——Meilisearch 已在 compose 中跑起来（`:7700`），配置项已存在
- **前置**：nodes 已落库（60 条）。`contents` 正文（05）还没好 → **本波只索引 nodes**，正文索引后补

## 目标

让门户「找得到」：把节点索引进 Meilisearch，提供 `GET /v1/search`，门户加搜索入口与结果页。

## 独占文件

- `apps/api/app/api/v1/search.py`（**新建**）、`apps/api/app/services/**`（**新建目录**）
- `apps/web/app/search/**`（**新建**）、`apps/web/app/page.tsx`（**仅加搜索入口**）

## 不要动

- `apps/api/app/api/v1/nodes.py` 等既有端点、`apps/api/app/core/**`
  （`MEILISEARCH_HOST` / `MEILISEARCH_API_KEY` **配置已存在**，直接用；需要新配置项先找主控）
- `apps/admin/**`、`apps/importer/**`、`docker-compose.yml`、骨架 JSON、主文档

## 步骤

> 环境：`node_modules` 与 `apps/api` 的 `.venv` 已由主控预装；**不要自己起 compose、不要抢端口**。

1. **用现成 SDK**：Python 侧用官方 `meilisearch` 包（MIT）——**不自己封装 REST**。
2. **建索引**：`nodes` 索引，字段 `slug/title/summary/discipline/stage/tradition`
   - `searchableAttributes=[title, summary]`
   - `filterableAttributes=[discipline, stage, tradition]`
   - 提供**一次性全量索引**入口（脚本或子命令），**不做实时同步**（Directus hooks 以后再说）
3. **端点** `GET /v1/search?q=&limit=&discipline=&stage=&tradition=`
   - 返回**统一信封** `{success, data, meta, error}`；`data` 为命中节点数组，形状对齐共享类型 `KnowledgeNode`
4. **降级**：Meilisearch 不可达时**不许 500**，返回空结果 + `meta.degraded=true`
5. **门户**：首页加搜索框 → `/search?q=` 结果页；复用现有 `components/NodeList` 与 `lib/api/` 的 `safe()` 降级模式

## 验收标准

- `GET /v1/search?q=医学` 命中 > 0；`?q=nonexistent-xyz` 返回空且 HTTP 200
- **停掉 Meilisearch 后端点仍 200**（降级，不报错）
- `pnpm --filter web build` 通过；`/search?q=` 页面可用
- 既有端点行为零改动

## 注意

- 新增依赖必须成熟且 MIT/Apache-2.0（官方 `meilisearch` 包满足）
- 验收由主控在新栈执行
