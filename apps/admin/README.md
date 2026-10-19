# apps/admin · Directus 后台 / 数据层

Directus 是内容数据的**唯一管理者**：建表、REST/GraphQL、用户与权限都在这里。
本目录存放**版本可控的 schema 快照**与一键 apply 脚本，便于换台机器复现。

```
apps/admin/
├── schema/snapshot.yaml     # Directus schema 快照（collections + fields + relations）
└── scripts/apply.ps1        # 一键 apply（拉起依赖 → apply 快照 → 配公共只读权限）
```

## 一键 apply 到新环境

前置：已装 Docker Desktop（含 `docker compose`）、Node 侧 `pnpm install` 已完成。

```powershell
# Windows（PowerShell 7）
pwsh -File apps/admin/scripts/apply.ps1
# 只 apply schema，不配公共权限
pwsh -File apps/admin/scripts/apply.ps1 -SkipPermissions
```

脚本做的事（等价的手工命令见下）：

1. `docker compose up -d mysql directus`（用仓库现有 compose，未修改）
2. 等 MySQL 就绪；Directus 就绪（compose 里 `directus` **没有 restart 策略**，MySQL 未就绪时它会退出，脚本会自动补一次 `docker compose start directus`）
3. 复制快照进容器 → `node /directus/cli.js schema apply --yes /directus/uploads/schema-snapshot.yaml`
   全新数据库若报 `Directus isn't installed on this database`，脚本会先跑 `node /directus/cli.js bootstrap`
4. 给 Public 政策补 `nodes` / `contents` 的 `read` 权限（幂等）

Linux / macOS 手工等价命令：

```bash
docker compose up -d mysql directus
docker compose exec -T mysql mysqladmin ping -uroot -ppassword        # 等到 alive
docker compose cp apps/admin/schema/snapshot.yaml directus:/directus/uploads/schema-snapshot.yaml
docker compose exec directus node /directus/cli.js schema apply --yes /directus/uploads/schema-snapshot.yaml
# 新建库需先：docker compose exec directus node /directus/cli.js bootstrap
```

导出/更新快照（改了字段后重新固化）：

```bash
docker compose exec directus node /directus/cli.js schema snapshot /directus/uploads/schema-snapshot.yaml
docker cp directus-directus-1:/directus/uploads/schema-snapshot.yaml apps/admin/schema/snapshot.yaml
```

## 两个注意点

- **权限不在快照里**：Directus schema 快照只含 `collections / fields / relations`；角色权限属于**数据**，所以由 `apply.ps1` 的第 4 步补齐（Public 政策 UUID 固定为 `abf8a154-5b1c-4a46-ac9c-7300570f4f17`）。
- **权限的 `fields` 必须写 `*`**：Directus 12.5 把「字段级自定义权限规则」列为受限资源，传具体字段名会返回
  `RESOURCE_RESTRICTED: custom_permission_rules_enabled is a restricted resource`。传 `*` 可正常创建。
- 写权限（增删改）只留给管理员，公共只读仅覆盖 `nodes` / `contents`。

## 数据契约（给下游分支：content-import / 端点）

Directus 建的是 **snake_case** 列；FastAPI `/v1` 输出转 **camelCase**。以下是当前实际列名与类型
（取自 `information_schema`，`apps/admin/schema/snapshot.yaml` 为权威定义）。

### nodes

| 列 | 类型 | 空 | 默认 | 说明 |
|---|---|---|---|---|
| id | int unsigned | 否 | 自增 | 主键 |
| type | varchar(64) | 否 | — | concept / path / resource / topic |
| slug | varchar(255) | 否 | — | **唯一索引**，URL 用稳定标识 |
| title | varchar(255) | 否 | — | |
| summary | text | 是 | — | |
| stage | varchar(64) | 是 | — | 取值对齐骨架：preschool / learning / research / change |
| discipline | varchar(64) | 是 | — | 取值对齐骨架 12 学科 id，如 health_medicine |
| tradition | varchar(64) | 否 | empirical | empirical / holistic / experiential / speculative / devotional |
| language | varchar(16) | 否 | zh | |
| status | varchar(32) | 否 | draft | draft / review / published |
| source_id | varchar(255) | 是 | — | 来源开放知识库条目 ID（如 Wikidata QID） |
| source_url | varchar(1024) | 是 | — | 来源链接 |
| created_at | timestamp | 是 | — | Directus `date-created`，自动写入 |
| updated_at | timestamp | 是 | — | Directus `date-updated`，自动写入 |

### edges

| 列 | 类型 | 空 | 默认 | 说明 |
|---|---|---|---|---|
| id | int unsigned | 否 | 自增 | 主键 |
| source_node | int unsigned | 否 | — | 外键 → `nodes.id`（`edges_source_node_foreign`） |
| target_node | int unsigned | 否 | — | 外键 → `nodes.id`（`edges_target_node_foreign`） |
| relation | varchar(64) | 否 | — | prerequisite / related / contrasts / part_of |
| weight | float(10,5) | 是 | — | 权重（可选） |

### contents

| 列 | 类型 | 空 | 默认 | 说明 |
|---|---|---|---|---|
| id | int unsigned | 否 | 自增 | 主键 |
| node | int unsigned | 否 | — | 外键 → `nodes.id`（`contents_node_foreign`） |
| body_ref | varchar(512) | 是 | — | 正文文件在文件系统中的路径（正文本体由 Git 管理） |
| format | varchar(32) | 否 | mdx | mdx / markdown |
| version | int | 否 | 1 | 正文版本号 |
| checksum | varchar(64) | 是 | — | 正文 sha256，用于校验引用文件 |
| status | varchar(32) | 否 | draft | draft / review / published |

外键删除策略统一为 `NO ACTION`（在 Directus 里显式配的），删节点前需先清掉引用它的 edges / contents。

> 注：`packages/types` 的 `KnowledgeEdge` 字段为 `id / sourceId / targetId / relation / weight`，
> 即数据库列 `edges.source_node / target_node / relation / weight` 经 `/v1` 转 camelCase 后的形状。
