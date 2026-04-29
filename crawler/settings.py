import os
import sys
from pathlib import Path

# ── Reactor must be installed before anything else touches Twisted ──────────
from scrapy.utils.reactor import install_reactor
install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

BOT_NAME = "llmscrawler"
SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

# ── Playwright download handlers ─────────────────────────────────────────────
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = int(
    os.environ.get("PLAYWRIGHT_TIMEOUT_MS", 15_000)
)
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 LLMsCrawler/1.0"
        ),
        "java_script_enabled": True,
        "ignore_https_errors": True,
    }
}
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4

# ── Concurrency ───────────────────────────────────────────────────────────────
CONCURRENT_REQUESTS = int(os.environ.get("CONCURRENT_REQUESTS", 16))
CONCURRENT_REQUESTS_PER_DOMAIN = int(os.environ.get("CONCURRENT_REQUESTS_PER_DOMAIN", 4))
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_DELAY = 0  # handled per-domain by ratelimit middleware

# ── Middleware stack ──────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    # Disable Scrapy's built-in retry — we use our own
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    # Our custom chain — order matters
    "crawler.middlewares.robots_middleware.RobotsMiddleware": 100,
    "crawler.middlewares.ratelimit_middleware.RateLimitMiddleware": 200,
    "crawler.middlewares.playwright_middleware.PlaywrightFallbackMiddleware": 300,
    "crawler.middlewares.retry_middleware.FallbackRetryMiddleware": 400,
}

ITEM_PIPELINES = {
    "crawler.pipelines.dedup_pipeline.DedupPipeline": 100,
    "crawler.pipelines.content_pipeline.ContentPipeline": 300,
    "crawler.pipelines.classify_pipeline.ClassifyPipeline": 400,
    "crawler.pipelines.storage_pipeline.StoragePipeline": 900,
}

EXTENSIONS = {
    "crawler.extensions.stats_extension.StatsExtension": 500,
}

# ── Scheduler: BFS so shallow pages are crawled first ────────────────────────
SCHEDULER_DISK_QUEUE = "scrapy.squeues.PickleFifoDiskQueue"
SCHEDULER_MEMORY_QUEUE = "scrapy.squeues.FifoMemoryQueue"

# ── Robots.txt — enforced in our custom middleware, not Scrapy built-in ───────
ROBOTSTXT_OBEY = False  # we handle it ourselves for Crawl-delay + Sitemap parsing

# ── Depth ─────────────────────────────────────────────────────────────────────
DEPTH_LIMIT = int(os.environ.get("DEPTH_LIMIT", 3))
DEPTH_STATS = True

# ── Misc ──────────────────────────────────────────────────────────────────────
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

DB_PATH = os.environ.get("CRAWLER_DB_PATH", "crawl.db")
MAX_PAGES = int(os.environ.get("MAX_PAGES", 500))
MAX_PAGES_PER_DOMAIN = int(os.environ.get("MAX_PAGES_PER_DOMAIN", 100))
RATE_LIMIT_PER_DOMAIN = float(os.environ.get("RATE_LIMIT_PER_DOMAIN", 2.0))
PLAYWRIGHT_FORCED_DOMAINS: list[str] = []
MIN_WORDS_FOR_HTTP = int(os.environ.get("MIN_WORDS_THRESHOLD", 50))
FOLLOW_EXTERNAL_LINKS = os.environ.get("FOLLOW_EXTERNAL_LINKS", "false").lower() == "true"
