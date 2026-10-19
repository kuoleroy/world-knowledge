# 任务书 10d · 未覆盖学科正文（contents · MDX）· 生活·农业组

- **分支**：`kuoleroy/content-life`
- **worktree**：`E:\wk\clife`
- **波次**：第四波（11 学科正文，4 组并行）
- **本组学科**：`life_experience`（58）· `agriculture_food`（56），合计 **114 篇**
- **前置**：节点已落库（主控已完成 12 学科 677 节点 + 跨学科去重）；任务书 **05（contents-mdx）已完工**——
  `python -m importer mdx` 子命令与写入通道**已在 main 就绪**，本波**只做改写，不改任何代码**。
- **素材**（主控已预置到本 worktree；`out/` 是 gitignored，仅本地存在）：
  - `apps/importer/out/<discipline>/nodes.jsonl` —— 每行一个节点：`slug / title / summary / stage / tradition / source_url …`
  - `apps/importer/out/<discipline>/wiki/<slug>.json` —— Wikipedia 摘要素材：`extract / url / description / license / attribution`

## 目标

为本组的**每一个节点**产出一篇**自撰中文 MDX 导语**，落盘到
`apps/importer/content/<discipline>/<slug>.mdx`（committed，即正文权威源）。
主控随后用 `python -m importer mdx --discipline <discipline> --yes` 幂等写入 `contents` 表。

## 独占文件

- `apps/importer/content/life_experience/**`
- `apps/importer/content/agriculture_food/**`

## 不要动（否则会与其它分支 / 主控冲突）

- 任何 `apps/api/**`、`apps/web/**`、`apps/admin/**`、`docker-compose.yml`
- `apps/importer/importer/**`、`apps/importer/config/**`、`apps/importer/tests/**`（05 已封版，交棒完成）
- `packages/types/**`、`apps/api/app/data/skeleton/*.json`、主文档 `世界知识门户项目知识文档.md`
- **不要动 `apps/importer/out/**`**（素材只读；且已 gitignore，不要提交）

## 交付要求（每篇）

1. **文件名 = `<slug>.mdx`**，`slug` 取自 `nodes.jsonl` 的 `slug` 字段（如 `wd-Q11410`）；
   必须与节点**一一对应**——**一个不多、一个不少**。
2. **篇幅 150–300 字**（中文按字符计）。硬上限 512（`body_ref` 是 varchar(512)）。
3. **结构**：一句话导语 + 2–4 个要点（小标题或列表），末尾保留来源入口：
   `> 来源：[<title>](<source_url>)`
4. **必须自撰，禁止照搬**：`wiki/<slug>.json` 里的 `extract` 是 **CC BY-SA 4.0** 素材，
   直接搬运会引入署名 / 许可证义务。只能把它当「事实来源」，用**自己的话**重写；
   **不得**逐句翻译、**不得**整段复制粘贴。
5. **口径**：面向「不分国家 / 阶层 / 年龄」的普通读者，通俗、克制、就事论事；
   不用营销腔（"最"、"必学"、"神器"…），不加编者按，不写"本文 / 笔者"。
6. **缺素材兜底**：若某节点缺 `wiki/<slug>.json`，用 `nodes.jsonl` 的
   `title` + `summary` + `source_url` 自撰，**切勿编造事实**。本组缺失清单：**无**。

## 样板（取自已交付的 health_medicine，作风格参照）

`apps/importer/content/health_medicine/wd-Q10405662.mdx`（182 字）：

```
片仔癀是产自福建漳州的中药，因疗效显著而享誉海内外，是国家一级保护的中药品种之一，亦为中国地理标志产品。其组方与制作工艺被列为保密范畴，常用于热毒肿痛类证候的调理，是代表性名优中成药。

- 产地：福建漳州
- 地位：国家一级保护中药品种
- 标识：中国地理标志产品

> 来源：[维基百科](https://zh.wikipedia.org/wiki/片仔癀)
```

## 自检

- 逐学科核对：`content/<discipline>/` 的 `.mdx` 集合 **==** `out/<discipline>/nodes.jsonl` 的 `slug` 集合
- 每篇字数在 150–300；每篇末尾有 `> 来源：[...](...)`
- 确认**没有**把 `extract` 的整段原文搬进正文
- 库写入（dry-run / 真写）与索引重灌**由主控统一执行**；本波**不要求**你起 compose、装依赖、连数据库

## 提交

- `git add apps/importer/content/life_experience apps/importer/content/agriculture_food`
- 提交信息：`content(life): 新增 life/agri 两学科自撰 MDX（114 篇）`
- **只提交 `content/**`**；不要 `git add -A`（避免带上 `out/` 或其它无关文件）

## 注意

- 新增依赖：**不需要**（纯文本改写）
- 依赖 / 环境由主控统一提供；**不要**自行安装依赖、起 Docker、占用端口
