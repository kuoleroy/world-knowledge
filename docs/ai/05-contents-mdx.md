# 任务书 05 · 知识正文（contents · MDX）

- **分支**：`kuoleroy/contents-mdx`
- **worktree**：`E:\wk\contents`
- **波次**：**可立即起步**——03（content-import）已完工合并，`apps/importer/**` 交棒给本波
- **前置**：nodes 已落库（新栈 60 条 `health_medicine`）；改写素材 59 份在 `apps/importer/out/health_medicine/wiki/<slug>.json`

## 目标

把门户从「能读进去」做实：为每个节点产出一篇**中文 MDX 导语**，写入 `contents` 表，让 `/node/<slug>` 显示真实正文（渲染器已在位，见 13.8）。

## 独占文件

- `apps/importer/**`（03 已完工，本波接棒）

## 不要动

- `apps/api/**`、`apps/web/**`、`apps/admin/**`、`docker-compose.yml`
- `packages/types/index.ts`、`apps/api/app/data/skeleton/*.json`、主文档

## 步骤

> 环境：`apps/importer` 的 `.venv` 已预装（主控提供），**不要自己起 compose、不要抢端口**。

1. **复用 03 的写库通道**：沿用现有 Directus 客户端与幂等逻辑，新增子命令
   `python -m importer mdx --discipline health_medicine [--yes]`（不加 `--yes` 只 dry-run）。
2. **取素材**：`out/<discipline>/wiki/<slug>.json`（`extract` / `url` / `license` / `attribution`）+ `nodes.jsonl` 的 `title`/`summary`；17 条无 summary 的用 Wikidata 描述兜底。
3. **改写（本波真正的工作量）**：每条产出 150–300 字中文 MDX：
   - **禁止照搬维基原文**——CC BY-SA 4.0 要求署名，照搬即受其约束；必须自撰
   - 结构：一句话导语 + 2–4 个要点（可用小标题/列表）
   - 正文末尾保留 `source_url` 作为来源入口
4. **落库**：`contents` 列 `id, node, body_ref, format, version, checksum, status`
   - `body_ref` 用**原始 MDX 字符串**（13.8 三选一之一；**文件系统路径不可渲染**）
   - `format='mdx'`、`checksum=sha256(body)`、`version` 单调递增
   - **主控裁定：AI 改写稿一律 `status='draft'`**（待人工/社区审校后再转 `published`）
   - 幂等键 `node`（每节点 1 条；重复跑只 PATCH 有差异字段）
5. **落盘留档**：同时把 MDX 写到 `out/<discipline>/mdx/<slug>.mdx`（版本可控）

## 验收标准

- `python -m importer verify --discipline health_medicine` 仍通过
- `python -m importer mdx --discipline health_medicine --yes` **幂等**：复跑 = `新建 0 / 更新 0 / 无变化 60`
- `contents` 60 行；`/node/<slug>` 渲染出正文（非占位）
- 正文**不照搬**维基原文；`body_ref` 为 MDX 字符串

## 注意

- 新增依赖必须成熟且 MIT/Apache-2.0；**本波不需要新增依赖**
- 验收由主控在新栈执行（`docker compose` 已由主控拉起）
