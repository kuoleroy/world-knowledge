# apps/importer · 开放知识库内容导入

任务书：[`docs/ai/03-content-import.md`](../../docs/ai/03-content-import.md)

从开放知识库抓条目 → 按 `stage × discipline × tradition` 标注 → 产出可直接写入 `nodes` 表的 JSONL。
**不自己从零编内容**；学科 id / 阶段 id / 传统 id 全部来自骨架 JSON（`apps/api/app/data/skeleton/*.json`，只读）。

```
抓取（Wikidata SPARQL）──► 过滤 / 合并 ──► 标注（taxonomy.yaml 规则）──► 落盘 JSONL
        └── Wikipedia REST summary（改写素材，旁路落盘，不入库）
```

## 一条命令跑一次导入

```powershell
# 工作目录：apps/importer（venv 在仓库根）
cd E:\wk\importer\apps\importer
..\..\.venv\Scripts\python.exe -m importer run --discipline health_medicine --limit 60
```

国内网络直连 Wikimedia 会超时，需要本地代理时加 `--proxy`（或先设 `HTTPS_PROXY`）：

```powershell
..\..\.venv\Scripts\python.exe -m importer run --discipline health_medicine --limit 60 --proxy http://127.0.0.1:7890
```

其他子命令：

```powershell
# 校验配置：id 是否都来自骨架 JSON、规则与种子是否自相矛盾（不联网）
..\..\.venv\Scripts\python.exe -m importer check

# 联网核对种子 QID 的中文标签有没有漂移（改过 Wikidata 后建议跑一次）
..\..\.venv\Scripts\python.exe -m importer check --online --proxy http://127.0.0.1:7890

# 写入库（步骤 4，**等 01 的 nodes 表合并进 main 后再跑**；不加 --yes 是 dry-run）
..\..\.venv\Scripts\python.exe -m importer push --discipline health_medicine --yes
```

> 首次运行/换网络后建议先 `check --online`，种子 QID 若被上游合并或改标签会立刻暴露。

## 产出

```
apps/importer/out/<discipline>/
  nodes.jsonl        待入库记录：只有 nodes 表字段，一行一条，可直接 upsert
  annotations.jsonl  每条标注的依据（走哪条规则、命中哪个关键词、属于哪个种子）
  wiki/<slug>.json   Wikipedia 摘要素材（CC BY-SA 4.0，改写用，**不直接入库**）
  summary.json       本次运行参数、阶段/传统分布、跳过原因统计、文件清单
```

`nodes.jsonl` 的一行（字段与 `apps/api/app/models/node.py` 的 `nodes` 表一致）：

```json
{"slug":"wd-Q200253","type":"concept","title":"中医学","summary":"中國傳統醫學",
 "stage":"learning","discipline":"health_medicine","tradition":"holistic",
 "language":"zh","status":"draft","source_id":"Q200253",
 "source_url":"https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%8C%BB%E5%AD%A6"}
```

### slug 规则

`wd-<QID>`，例如 `wd-Q12345`。**只由来源主键推导，不含标题**——标题后续被改写/翻译后
slug 不变，URL 与幂等 upsert 都安全。非 Wikidata 来源将来用 `<来源前缀>-<ID>`（如 `oa-W123`）。

## 标注怎么改

全部规则在 [`config/taxonomy.yaml`](config/taxonomy.yaml)，改完重跑即可，代码里没有硬编码关键词。

| 块 | 作用 |
|---|---|
| `defaults` | 产出字段默认值（`language` / `node_type` / `status` / 兜底 `stage`） |
| `filters` | 质量门槛：`min_sitelinks`、是否必须有中文标签/中文维基条目、`exclude_qids` 黑名单（附理由） |
| `stage_rules` | 关键词 → 阶段，**顺序即优先级**，先命中先用 |
| `tradition_rules` | 关键词 → 传统，顺序即优先级 |
| `disciplines.<id>.seeds` | 学科 = 一批人工挑的 Wikidata 根条目；条目继承种子的学科与传统，种子条目的阶段可人工钉死 |

标注优先级：

1. **传统**：先匹配 `tradition_rules`；一个都不中，才用种子的 `tradition`。
2. **阶段**：种子条目本身（QID 相同）用种子的 `stage` 钉死；其余条目匹配 `stage_rules`；
   再不中，用 `defaults.stage`。
   > 钉死只作用于种子条目本身，**不向子树扩散**——阶段是编辑判断，硬塞给整棵子树会把上游
   > 噪声（例如 Wikidata 里被误标成儿科学子类的「免疫学」）一起染成学前阶段。
3. **学科**：永远取种子的 `discipline`（不做关键词猜测——种子是最可控的人工入口）。

种子还有两个旋钮：

- `min_sitelinks`：该种子自己的站点链接数下限（默认取 `filters.min_sitelinks`）。
- `include_subclasses`：是否把「直接子类」也算进子树。默认 `false`——Wikidata 的 `P279`
  边噪声很大（「免疫学」被标成「儿科学」子类就是这样来的），只给概念型种子
  （中医学、阿育吠陀、医学研究）打开，否则「中药」「气功」这类真正的内容条目会漏。

`annotations.jsonl` 里每条都写了 `reasons`，例如
`tradition=holistic ← 关键词「针灸」命中规则：命中整体·生命传统关键词`，方便复核和申诉。

**选片策略**：候选按传统分组后**轮转取样**，再按「阶段 → 传统 → 站点链接数」排序落盘。
原因是门户把各知识传统**平级并列**，不能让站点链接数最高的「疾病/医学」一堆实证条目
把别的传统挤没（否则 `health_medicine` 会 80% 是 `empirical`）。

## 来源、许可与署名（重要）

| 来源 | 用途 | 许可 | 署名要求 |
|---|---|---|---|
| **Wikidata** | QID（主键）、中文标签、中文描述（→ `nodes.summary`） | **CC0** | 无署名义务；`source_id` 记录 QID，`source_url` 指向维基条目 |
| **Wikipedia** | 正文摘要（→ `out/.../wiki/*.json`，仅作改写/翻译素材） | **CC BY-SA 4.0** | **必须署名**并以相同许可共享；发布时保留原条目链接与编辑历史入口 |

因此设计上做了切分：

- `nodes.summary` 只放 **Wikidata 描述（CC0）**，避免把 CC BY-SA 正文直接搬进门户；
- 维基正文单独落盘，每条都带 `license` / `attribution` / `url` / `retrieved_at` / `note`，
  供 04（节点详情 MDX）或人工改写时取用；**改写后的文字不再受 BY-SA 约束**，但引用原文时仍然要署名。

抓取礼节：带可识别 `User-Agent`（缺了会被 Wikimedia 直接 403）、请求间隔 ≥0.4s、失败指数退避、
结果落 `.cache/` 避免重复打接口。缓存与产出都不进制（见 `.gitignore`）。

## 写入库（步骤 4，已落库）

**方式选择：走 Directus `/items/nodes` REST，不直连 MySQL。** 理由：

1. 规范铁律「CRUD / 数据管理归 Directus，FastAPI 只读」——写入口应当唯一；
2. 权限、审计、字段校验由 Directus 负责，importer 不必持有数据库凭据，只要一个管理员 token；
3. 换机器复现只要一个 URL + 一个 token。

**幂等**：以 `source_id`（= QID）为业务键「先查后写」——查到就 PATCH 有差异的字段，
查不到才 POST，字段全一致则跳过；`slug` 形如 `wd-<QID>`，与 `source_id` 一一对应。

**约束**：`edges.source_node/target_node`、`contents.node` 对 `nodes.id` 是 `NO ACTION` 外键，
**删节点前必须先清 `edges` / `contents`**；本模块只做 insert / 有差异的 update，不删不改外键数据。

```powershell
cd E:\wk\importer\apps\importer
# 1) 取管理员 token（写权限仅管理员；public 角色只读）
$login = Invoke-RestMethod -Uri 'http://localhost:8055/auth/login' -Method Post `
  -ContentType 'application/json' `
  -Body '{"email":"admin@worldknowledge.org","password":"password"}'
$env:DIRECTUS_URL = 'http://localhost:8055'
$env:DIRECTUS_TOKEN = $login.data.access_token

# 2) 先 dry-run（只查不写），确认「将新建 N / 将更新 0」
..\..\.venv\Scripts\python.exe -m importer push --discipline health_medicine

# 3) 真写
..\..\.venv\Scripts\python.exe -m importer push --discipline health_medicine --yes
```

**落库记录（2026-10-19，主控绿灯后执行）**

| 项 | 结果 |
|---|---|
| 首次写入 | 60 条全部新建（`nodes.id` 5–64，加上 01 的 3 条样例共 63 行），0 失败 |
| 幂等复跑 #2 | 新建 0 / 更新 0 / 无变化 60 |
| 幂等复跑 #3 | 新建 0 / 更新 0 / 无变化 60 |
| 重复检查 | `slug` 无重复、`source_id` 无重复；`stage/discipline/tradition/source_id/source_url/title` 无空值 |
| 内容指纹 | 两次复跑前后 60 行管理字段 sha256 完全一致（`c22cfc52…61d5`） |
| 门户读路径 | 匿名（无 token）`GET /items/nodes?filter={"stage":{"_eq":X},"discipline":{"_eq":"health_medicine"}}` → preschool 2 / learning 36 / research 3 / change 19 |
| `/v1/nodes` | 返回 63 行，字段转 camelCase（`sourceId`/`sourceUrl`/`createdAt`），与 `packages/types` 的 `KnowledgeNode` 对齐 |

## 测试

```powershell
cd E:\wk\importer\apps\importer
..\..\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

纯离线（假 Fetcher，不发网络请求），覆盖：slug 规则、标注优先级、骨架 id 校验、
重复运行逐字节幂等、限流取样、黑名单与过滤跳过计数。

## 目录

```
apps/importer/
  importer/
    cli.py            命令行（run / check / push）
    config.py         两个 YAML 的加载与校验（校验失败直接报错，不出脏数据）
    skeleton.py       只读骨架 JSON，供 id 校验
    models.py         Seed / RawItem / Annotation / NodeDraft
    annotate.py       规则匹配（不含硬编码关键词）
    pipeline.py       抓取→过滤→标注→落盘，含轮转取样
    net.py            httpx 客户端：UA、限流、重试、缓存
    output.py         原子写 JSONL/JSON
    sources/
      wikidata.py     SPARQL 子树查询
      wikipedia.py    REST summary（改写素材）
    writers/
      directus.py     幂等 upsert（待 01 合并后联调）
  config/
    sources.yaml      端点 / UA / 代理 / 限流
    taxonomy.yaml     阶段×学科×传统 的规则与种子（人工校正入口）
  tests/              离线单元测试
  requirements.txt    httpx==0.28.1 / PyYAML==6.0.3（仓库根 .venv 已预装）
```

## 已知限制 / 待确认

1. **阶段分布天然偏 `learning`**：维基百科的医学条目大多是「系统掌握」型概念，`research`
   （临床试验、循证医学）/`preschool` 的候选本来就少。当前 60 条示例为
   `learning 36 / change 19 / research 3 / preschool 2`，四个阶段都有但不均衡。
   要调平衡，改 `taxonomy.yaml` 的规则或给种子加 `stage` 即可，不需要动代码。
2. **简繁混排**：Wikidata 的中文描述常只有繁体（`zh`），标签优先取简体（`zh-hans/zh-cn`），
   所以个别 `summary` 会是繁体。要么接受，要么等 04 用维基正文改写后覆盖。
3. **没有中文描述就留空 `summary`**：默认不拿英文描述凑数（`filters.allow_en_summary: false`），
   首批 60 条里有 17 条留空，需后续补写。
4. **上游关系噪声**：Wikidata 的 `P31/P279/P361` 边并不总对（「免疫学」被标成「儿科学」子类、
   「无国界医生」挂在医学子树下）。已用 `exclude_qids` 挡掉确认的几条，并把
   `include_subclasses` 默认关闭；剩余噪声属于内容策展长尾。
5. **`type` 一律 `concept`**：区分 concept / topic / resource 需要更细的信号（如是否有人物/组织类型），
   目前不猜；`defaults.node_type` 可整体切换。
6. **每个 QID 只对应 `nodes` 一行**：同一传统/学科下不重复建节点；跨学科复用同一概念时，
   将来需要 `nodes ↔ disciplines` 多值关系（当前表结构是一对一字符串），属于表结构议题。
7. **`/v1/nodes` 暂不支持 `discipline` 过滤**（只支持 `type/stage/tradition/slug`，也不支持分页）。
   「阶段 × 学科」导航页若走 FastAPI，需要 04 补一个 `discipline` 查询参数；走 Directus
   `/items/nodes?filter=...` 则已可用（已验证匿名可读、按 stage×discipline 过滤正确）。
   该端点属 `apps/api/**`，不在本分支范围内 → **请求主控协调**。
