import logging
import sqlite3
from scrapy import signals
from scrapy.exceptions import NotConfigured
from storage.db import get_connection, insert_log, get_control_action, clear_control

logger = logging.getLogger(__name__)


class StatsExtension:
    """
    Writes periodic stats to SQLite logs table.
    Polls the control table to handle stop/pause signals from the dashboard.
    """

    def __init__(self, db_path: str, crawler):
        self.db_path = db_path
        self.crawler = crawler
        self.conn: sqlite3.Connection | None = None

    @classmethod
    def from_crawler(cls, crawler):
        db_path = crawler.settings.get("DB_PATH", "crawl.db")
        ext = cls(db_path, crawler)
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(ext.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        return ext

    def spider_opened(self, spider):
        from storage.db import init_db
        init_db(self.db_path)
        self.conn = get_connection(self.db_path)
        self._log("INFO", "Crawl started", spider.name)

    def spider_closed(self, spider, reason):
        self._log("INFO", f"Crawl finished: {reason}", spider.name)
        if self.conn:
            self.conn.close()

    def spider_idle(self, spider):
        """Check for dashboard control signals on each idle tick."""
        if not self.conn:
            return
        action = get_control_action(self.conn)
        if action == "stop":
            logger.info("Dashboard stop signal received")
            with self.conn:
                clear_control(self.conn)
            self.crawler.engine.close_spider(spider, "dashboard_stop")
        elif action == "pause":
            logger.info("Dashboard pause signal received")
            with self.conn:
                clear_control(self.conn)
            self.crawler.engine.pause()

    def item_scraped(self, item, spider, response):
        stats = self.crawler.stats.get_stats()
        crawled = stats.get("item_scraped_count", 0)
        if crawled % 50 == 0:
            self._log(
                "INFO",
                f"Progress: {crawled} pages crawled | "
                f"queued={stats.get('scheduler/enqueued', 0)} | "
                f"failed={stats.get('downloader/exception_count', 0)}",
                spider.name,
            )

    def _log(self, level: str, message: str, spider: str = "") -> None:
        if self.conn:
            try:
                with self.conn:
                    insert_log(self.conn, level, message, spider)
            except Exception as exc:
                logger.error("StatsExtension log error: %s", exc)
