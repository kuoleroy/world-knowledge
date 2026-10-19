# 任务书 01 · Directus 集合落地

- **分支**：`kuoleroy/directus-collections`
- **worktree**：`E:\wk\directus`
- **波次**：第一波（可与 02 并行）
- **前置**：无

## 目标

让 **Directus 成为内容数据的唯一管理者**：建 `nodes` / `edges` / `contents` 三张表并配好权限，使后端 `/v1/nodes` 能返回真实数据。

> 现状：`/v1/nodes` 返回空列表，因为表还不存在（DB 未启动时后端优雅降级为空）。

## 为什么是你

项目文档 1.8：**后台不自研**，数据管理的增删改查、用户权限、REST/GraphQL 全部交给 Directus。文档 4.2 已给出表结构定义。

## 独占文件（只准动这些）

- `apps/admin/**`
- `apps/api/app/models/**`（**仅校对字段映射**，不改端点）

## 不要动

- `docker-compose.yml` —— 归 `02` 分支。你直接用它起 Directus，**不改它**
- `packages/types/index.ts`、`apps/api/app/data/skeleton/*.json`、主文档
- `apps/api/app/api/v1/**`（端点归 04 / 主控）
- `apps/web/**`

## 步骤

1. **起依赖**：仓库根执行 `docker compose up -d mysql directus`（用现有 compose，不改它）。等 Directus 就绪，确认 http://localhost:8055 可登录（默认账号见 compose：`admin@worldknowledge.org` / `password`）。
2. **建集合**，字段严格按文档 4.2：
   - `nodes`：`id, type, slug(unique), title, summary, stage, discipline, tradition, language, status, source_id, source_url, created_at, updated_at`
   - `edges`：`id, source_node, target_node, relation, weight`
   - `contents`：`id, node, body_ref, format, version, checksum, status`
   - `stage` / `discipline` / `tradition` / `status` 用**字符串**，取值与骨架 JSON 的 id 对齐（`preschool`…/`health_medicine`…/`empirical`…）
3. **配权限**：给 `public` 角色对 `nodes`（必要时 `contents`）**只读**权限，让门户无需密钥即可读；写权限留给管理员。
4. **固化定义**：把 Directus schema 导出为快照放进 `apps/admin/`，并写一段「如何一键 apply 到新环境」的说明（版本可控，见文档 4.2 归属）。
5. **校对模型**：确认 `apps/api/app/models/node.py` 等与实际列名/类型一致（Directus 建的是 snake_case 列；FastAPI 输出转 camelCase）。
6. **造样例**：后台手动加 2-3 条 nodes（覆盖不同 stage / discipline / tradition），验证读链路。

## 验收标准

- `curl http://127.0.0.1:8000/v1/nodes` 返回非空（样例数据），字段与 `packages/types` 的 `KnowledgeNode` 对应
- Directus 后台 :8055 能对 nodes 增删改
- `apps/admin/` 下有 schema 快照 + apply 说明，换台机器可复现

## 给下游的交付契约（重要）

总结里**必须写清** `nodes` / `edges` / `contents` 的**最终列名与类型**，供 `kuoleroy/content-import` 分支写入。
