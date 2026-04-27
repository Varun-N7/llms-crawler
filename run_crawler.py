"""
CLI runner for the universal spider.

Usage:
    python run_crawler.py --url https://example.com
    python run_crawler.py --url https://example.com --depth 3 --max-pages 200
    python run_crawler.py --url https://a.com,https://b.com --profile docs_site
"""

import argparse
import os
import sys
import yaml
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "crawler.settings")


def load_profile(name: str) -> dict:
    path = Path(__file__).parent / "config" / "profiles" / f"{name}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def main():
    parser = argparse.ArgumentParser(description="LLMs Crawler")
    parser.add_argument("--url", required=True, help="Comma-separated seed URLs")
    parser.add_argument("--depth", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-pages-per-domain", type=int, default=None)
    parser.add_argument("--profile", default=None, help="Config profile name (docs_site, blog, ...)")
    parser.add_argument("--db", default="crawl.db", help="SQLite DB path")
    parser.add_argument("--no-playwright", action="store_true", help="Disable Playwright fallback")
    args = parser.parse_args()

    profile = load_profile(args.profile) if args.profile else {}
    crawl_cfg = profile.get("crawl", {})
    pw_cfg = profile.get("playwright", {})

    settings = get_project_settings()
    settings.set("START_URLS", args.url)
    settings.set("DB_PATH", args.db)
    settings.set("DEPTH_LIMIT", args.depth or crawl_cfg.get("max_depth", 3))
    settings.set("MAX_PAGES", args.max_pages or crawl_cfg.get("max_pages", 500))
    settings.set("MAX_PAGES_PER_DOMAIN", args.max_pages_per_domain or crawl_cfg.get("max_pages_per_domain", 100))
    settings.set("MIN_WORDS_FOR_HTTP", pw_cfg.get("min_words_threshold", 50))

    if args.no_playwright:
        settings.set("DOWNLOAD_HANDLERS", {})

    os.environ["CRAWLER_DB_PATH"] = args.db

    process = CrawlerProcess(settings)
    process.crawl("universal", start_urls=args.url)
    process.start()


if __name__ == "__main__":
    main()
