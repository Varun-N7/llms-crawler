import logging
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import requests as req_lib
import tldextract
from scrapy.http import Request

from crawler.spiders.base_spider import BaseSpider

logger = logging.getLogger(__name__)

_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap.xml.gz", "/sitemap/sitemap.xml"]
_SITEMAP_DEPTH_LIMIT = 3


class UniversalSpider(BaseSpider):
    """
    Entry-point spider. Accepts start_urls from CLI or settings.
    Discovers and processes sitemaps before crawling.
    """

    name = "universal"

    def __init__(self, start_urls: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        raw = start_urls or self.settings.get("START_URLS", "")
        self.start_urls = [u.strip() for u in raw.split(",") if u.strip()]
        if not self.start_urls:
            raise ValueError("Provide start_urls via -a start_urls=https://example.com")

    def start_requests(self):
        for url in self.start_urls:
            # First try to discover sitemap
            yield from self._probe_sitemaps(url)
            # Then crawl the seed URL itself
            yield Request(
                url,
                callback=self.parse,
                meta={"fallback_level": 0, "depth": 0},
                errback=self.errback,
                priority=10,
            )

    # ── Sitemap discovery ────────────────────────────────────────────────────

    def _probe_sitemaps(self, base_url: str):
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        # 1. robots.txt Sitemap: directives
        try:
            r = req_lib.get(f"{origin}/robots.txt", timeout=10, headers={"User-Agent": "LLMsCrawler"})
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sitemap_url = line.split(":", 1)[1].strip()
                        yield from self._parse_sitemap(sitemap_url, depth=0)
                        return  # found in robots.txt — stop probing
        except Exception:
            pass

        # 2. Try well-known paths
        for path in _SITEMAP_PATHS:
            url = origin + path
            try:
                r = req_lib.get(url, timeout=10, headers={"User-Agent": "LLMsCrawler"})
                if r.status_code == 200 and "<urlset" in r.text or "<sitemapindex" in r.text:
                    yield from self._parse_sitemap(url, depth=0, content=r.text)
                    return
            except Exception:
                continue

    def _parse_sitemap(self, url: str, depth: int, content: str | None = None):
        if depth > _SITEMAP_DEPTH_LIMIT:
            return

        try:
            if content is None:
                r = req_lib.get(url, timeout=15, headers={"User-Agent": "LLMsCrawler"})
                if r.status_code != 200:
                    return
                content = r.text

            root = ET.fromstring(content)

            # Sitemap index — recurse
            for sitemap in root.findall(".//sm:sitemap/sm:loc", _SITEMAP_NS):
                yield from self._parse_sitemap(sitemap.text.strip(), depth + 1)

            # URL set — emit requests with higher priority
            for loc in root.findall(".//sm:url/sm:loc", _SITEMAP_NS):
                page_url = loc.text.strip()
                if not self._over_limit(page_url):
                    yield Request(
                        page_url,
                        callback=self.parse,
                        meta={"fallback_level": 0, "depth": 1, "from_sitemap": True},
                        errback=self.errback,
                        priority=5,
                    )

        except Exception as exc:
            logger.warning("Sitemap parse failed for %s: %s", url, exc)
