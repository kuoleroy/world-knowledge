"""开放知识库内容导入（任务书 03）。

从 Wikidata 抓条目、从 Wikipedia 取改写素材，按 stage × discipline × tradition
标注后产出可直接写入 nodes 表的 JSONL。

写库一步见 ``importer.writers.directus``（等 01 分支的 nodes 表合并进 main 后再启用）。
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
