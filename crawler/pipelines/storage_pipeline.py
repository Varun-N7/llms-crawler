import logging
import sqlite3
from storage.db import get_connection, init_db, insert_page, insert_log

logger = logging.getLogger(__name__)


class StoragePipeline:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_path=crawler.settings.get("DB_PATH", "crawl.db"))

    def open_spider(self, spider):
        init_db(self.db_path)
        self.conn = get_connection(self.db_path)
        insert_log(self.conn, "INFO", f"Spider started: {spider.name}", spider.name)
        self.conn.commit()
        logger.info("StoragePipeline: DB at %s", self.db_path)

    def close_spider(self, spider):
        if self.conn:
            insert_log(self.conn, "INFO", f"Spider closed: {spider.name}", spider.name)
            self.conn.commit()
            self.conn.close()

    def process_item(self, item, spider):
        if self.conn is None:
            return item
        try:
            with self.conn:
                insert_page(self.conn, dict(item))
        except Exception as exc:
            logger.error("Failed to store %s: %s", item.get("url"), exc)
        return item
