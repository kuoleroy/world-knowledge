# 任务书 09 · 门户导航补全（模式 B + 关联展示）

- **分支**：`kuoleroy/portal-nav`
- **worktree**：`E:\wk\portal`
- **波次**：**可立即起步**——`apps/web` 无人占用（与 08 共目录但文件不重叠）
- **前置**：无硬依赖；关联展示用 `/v1/edges`（**已只读可用**，边数据可能为空，须优雅空态）

## 目标

补上设计文档里的「**模式 B：学科优先**」导航，并让节点详情页展示**关联节点**（关系边）。

## 独占文件

- `apps/web/app/page.tsx`、`apps/web/app/discipline/**`（**新建**）
- `apps/web/app/stage/**`、`apps/web/app/node/**`
- `apps/web/components/**`、`apps/web/lib/api/**`

## 不要动

- `apps/web/app/search/**`（**归 08**）、`apps/api/**`、`apps/admin/**`、`apps/importer/**`
- `docker-compose.yml`、`packages/types/index.ts`、骨架 JSON、主文档

## 步骤

> 环境：`node_modules` 已由主控预装；本地预览 `cd apps/web` 后 `pnpm exec next dev --port 3100`，**别占 `:3000`**。

1. **学科优先页**：新增 `/discipline/[discipline]`——列该学科内容，可按**阶段**筛选（复用 `FilterChips` 模式，状态走 URL query）。
2. **首页入口**：在「第一步 · 选择阶段」旁加「按学科浏览」入口（链到 `/discipline`），保持现有四阶段卡片不动。
3. **详情页关联**：`/node/[slug]` 用 `/v1/edges?source=<id>` / `?target=<id>` 展示前驱 / 后继 / 相关节点及 `relation`，**无边数据时显示空态不报错**。
4. **复用现有资产**：`components/`（`NodeList` / `FilterChips` / `ErrorNotice`）、`lib/api/` 的 `safe()` 降级、`lib/url.ts` 的 `withQuery`。
5. 阶段 / 学科中文名从 `/v1/stages`、`/v1/disciplines`（`nameZh`）取。

## 验收标准

- `pnpm --filter web build` 通过
- `/` 有**两个入口**（阶段优先 / 学科优先）；`/discipline/health_medicine` → 200 且列 60 条
- `/node/<slug>` 显示关联区块，**无边数据时不报错**
- 后端不可达时页面走 `safe()` **降级不崩**

## 注意

- **不做客户端状态管理**：导航 / 筛选状态一律走 URL query（与现有页面一致，链接可分享）
- 新增依赖须 MIT/Apache-2.0；预计**不需要新增依赖**
- 与 08 共占 `apps/web` 但文件不重叠；动手前先 `git merge main` 对齐
