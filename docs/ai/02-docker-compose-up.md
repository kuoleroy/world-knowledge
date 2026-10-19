# 任务书 02 · 全栈一键起（docker compose）

- **分支**：`kuoleroy/docker-compose-up`
- **worktree**：`E:\wk\compose`
- **波次**：第一波（可与 01 并行）
- **前置**：无

## 目标

一条命令在干净环境起全栈 —— `mysql + directus + meilisearch + api + web`，让门户也能容器化运行。

> 现状：compose 已有 `mysql` / `directus` / `api` / `meilisearch` 四个服务，**缺 `web`**。

## 独占文件

- `docker-compose.yml`
- `apps/web/Dockerfile`（新建）
- `apps/api/Dockerfile`（已有，校验并可修正）
- 启动文档：根 `README.md` 或 `docs/启动说明.md`
- 根 `.env.example`（可选）

## 不要动

- `apps/admin/**`（归 01）
- `apps/web/app/**`、`apps/web/components/**`、`apps/web/lib/**`（归 04）
- `packages/types/index.ts`、skeleton JSON、主文档

## 步骤

1. **给 `apps/web` 写多阶段 Dockerfile**。这是 pnpm monorepo，构建上下文必须包含根 `package.json`、`pnpm-workspace.yaml`、`pnpm-lock.yaml`、`packages/types`，再 `pnpm --filter web build`；运行阶段用 Next.js 产物启动。
2. **compose 加 `web` 服务**：端口 `3000:3000`，`depends_on: api`，环境变量 `NEXT_PUBLIC_API_BASE_URL` 指向 API 服务。
3. **校验各服务**：健康检查、`depends_on` 条件、数据卷、自定义网络、环境变量从 `.env` 注入。
4. **写启动说明**：一条 `docker compose up -d` + 各服务地址 + 首次初始化步骤（Directus 管理员账号等）。
5. **实际验证**。

## 验收标准

- `docker compose config` 无错
- 干净环境 `docker compose up -d` 后：
  - `:3000` 首页能出四阶段
  - `:8000/v1/stages` 返回 4 条
  - `:8055` Directus 后台可登录
  - `:7700` Meilisearch 可达
- 启动说明清晰、可复现

## 注意（易踩坑）

Docker 容器内 web 访问 API **不能用 `localhost`**，要用 compose 服务名（`http://api:8000`）；而宿主机浏览器用的是 `localhost:8000`。说明里要分别写清。（现有 `client.ts` 默认值是 `http://localhost:8000`，容器里需用环境变量覆盖。）
