# 世界知识门户 · 门户（Next.js）多阶段构建
# 构建上下文为仓库根（由 docker-compose.yml 的 build.context 指定），
# 必须包含：根 package.json / pnpm-workspace.yaml / pnpm-lock.yaml / packages/types。

# ---------------- 构建阶段 ----------------
FROM node:22-slim AS builder
WORKDIR /repo

# 可选：若构建环境处于代理之后，传入以下参数以便拉取 npm 包与 Google Fonts。
# 默认值空，普通直连环境不受影响。
ARG HTTPS_PROXY=
ARG HTTP_PROXY=
ENV HTTPS_PROXY=$HTTPS_PROXY
ENV HTTP_PROXY=$HTTP_PROXY

# 启用 pnpm（版本与根 package.json 的 packageManager 对齐）
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate

# 先拷依赖清单以最大化利用层缓存
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY packages/types/package.json packages/types/package.json
COPY apps/web/package.json apps/web/package.json

# 安装全量 workspace 依赖
COPY . .
RUN pnpm install --frozen-lockfile

# 容器内（服务端组件）访问 API 用 compose 服务名；同时作为构建期默认值（供客户端组件内联）
ARG NEXT_PUBLIC_API_BASE_URL=http://api:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# 构建 web 产物（输出到 apps/web/.next）
RUN pnpm --filter web build

# ---------------- 运行阶段 ----------------
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# 运行时覆盖：容器内访问 API / Directus 用 compose 服务名（compose 也会再注入一次）
ENV NEXT_PUBLIC_API_BASE_URL=http://api:8000
ENV NEXT_PUBLIC_DIRECTUS_URL=http://directus:8055

# 拷贝运行所需：根 node_modules（.pnpm 物理包 + 各 workspace 软链）、
# 以及 apps/web 自身的 node_modules（其 .bin/next 与 next 软链都在这层，pnpm 特有）。
# 注意：pnpm 把 next 的 bin 装在 apps/web/node_modules/.bin/next，而非根 node_modules/.bin。
COPY --from=builder /repo/node_modules ./node_modules
COPY --from=builder /repo/apps/web/node_modules ./apps/web/node_modules
COPY --from=builder /repo/packages/types ./packages/types
COPY --from=builder /repo/apps/web/package.json ./apps/web/package.json
COPY --from=builder /repo/apps/web/.next ./apps/web/.next
COPY --from=builder /repo/apps/web/public ./apps/web/public
COPY --from=builder /repo/apps/web/next.config.ts ./apps/web/next.config.ts

WORKDIR /app/apps/web
EXPOSE 3000

# 监听 0.0.0.0 供容器外访问；用 pnpm 生成的 next 启动脚本（位于 apps/web/node_modules/.bin/next）
CMD ["./node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
