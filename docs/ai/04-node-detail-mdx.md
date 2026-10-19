# 任务书 04 · 节点详情页 + MDX 正文

- **分支**：`kuoleroy/node-detail-mdx`
- **worktree**：`E:\wk\nodedetail`
- **波次**：第二波（代码可先写；要看效果需 `nodes` 有数据）
- **前置**：弱依赖 01

## 目标

把门户从「能列出」做到「能读进去」：新增**节点详情页**，渲染 MDX 正文，呈现阶段/学科/传统标签与来源。

## 独占文件

- `apps/web/**`（`app` / `components` / `lib`）
- `apps/api/app/api/v1/nodes.py`（**仅新增**按 `slug` 查询的能力，**不改**现有端点行为）

## 不要动

- `docker-compose.yml`、`apps/admin/**`、`apps/importer/**`
- `packages/types/index.ts`、skeleton JSON、主文档
- 其余 `apps/api/**`

## 步骤

1. **取数**：详情页需要按 `slug` 查节点。二选一，总结说明：
   - 给 `GET /v1/nodes` **新增** `slug` 查询参数（只新增，保持原有 `type`/`stage`/`tradition` 过滤不变）
   - 直接用 Directus `/items/nodes?filter[slug][_eq]=...`（前提：01 已配 public 只读）
2. **新增路由** `apps/web/app/node/[slug]/page.tsx`：展示 `title`、`summary`、阶段中文名、学科中文名、传统标签、来源链接。阶段/学科中文名从 `/v1/stages`、`/v1/disciplines` 取（学科中文名在 `nameZh` 字段）。
3. **MDX 正文**：从 `contents` 表取（`body_ref` 指向内容），渲染用现成库 —— `next-mdx-remote`（MIT）或官方 `@next/mdx`，择一并在总结说明。骨架期 `contents` 为空时**显示占位**，不要报错。
4. **打通入口**：从内容列表页把节点标题链到详情页。
5. **复用现有组件与风格**：`components/` 下已有 `FilterChips` / `NodeList` / `ErrorNotice`；沿用 `lib/api/` 的 `safe()` 降级模式。

## 验收标准

- `pnpm --filter web build` 通过
- `/node/<slug>` 能渲染：有数据显示全文，无数据显示占位而非报错
- 内容列表页可点进详情
- 后端不可达时仍优雅降级（沿用 `safe()`）

## 注意

- 新增依赖必须成熟且 MIT/Apache-2.0；**除 MDX 渲染库外尽量不加依赖**。
- 骨架期页面风格保持与现有四阶段/学科页一致。
