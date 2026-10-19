"""一次性全量索引入口（不做实时同步；Directus hooks 以后再说）。

在 ``apps/api`` 下运行::

    python -m app.services.reindex                 # 覆盖写入（自动建索引 / 更新 settings）
    python -m app.services.reindex --reset         # 删除索引后重建
    python -m app.services.reindex --batch-size 200

环境变量见 ``app.core.config``：``DATABASE_URL`` / ``MEILISEARCH_HOST`` /
``MEILISEARCH_API_KEY``。数据变更后重跑本命令即可。
"""

import argparse
import json
import logging
import sys

from meilisearch.errors import MeilisearchError
from sqlalchemy.exc import SQLAlchemyError

from app.services.indexer import DEFAULT_BATCH_SIZE, rebuild_index


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="把 MySQL 中的 nodes 全量索引进 Meilisearch")
    parser.add_argument("--reset", action="store_true", help="先删除索引再重建（settings 变更时用）")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="每批推送条数")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """执行全量索引；成功打印统一信封，失败返回非零退出码。"""
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        summary = rebuild_index(reset=args.reset, batch_size=args.batch_size)
    except (MeilisearchError, SQLAlchemyError) as exc:
        logging.error("索引失败：%s", exc)
        return 1
    print(
        json.dumps(
            {"success": True, "data": summary, "meta": {}, "error": None},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
