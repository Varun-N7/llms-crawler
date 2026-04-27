import logging
import re
from urllib.parse import urljoin, urlparse

import requests as req_lib
import tldextract
from scrapy import Spider
from scrapy.http import HtmlResponse, Request, Response

logger = logging.getLogger(__name__)

_PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


class BaseSpider(Spider):
    """
    Base spider with:
    - Fallback chain awareness (reads meta["fallback_level"])
    - requests-lib sync fallback in process_response override
    - Link extraction respecting follow_external_links setting
    - Domain page-cap tracking
    - PDF detection
    """

    name = "base"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page_counts: dict[str, int] = {}
        self._total = 0

    @property
    def max_pages(self) -> int:
        return self.settings.getint("MAX_PAGES", 500)

    @property
    def max_per_domain(self) -> int:
        return self.settings.getint("MAX_PAGES_PER_DOMAIN", 100)

    @property
    def follow_external(self) -> bool:
        return self.settings.getbool("FOLLOW_EXTERNAL_LINKS", False)

    def _domain(self, url: str) -> str:
        return tldextract.extract(url).registered_domain

    def _over_limit(self, url: str) -> bool:
        if self._total >= self.max_pages:
            return True
        domain = self._domain(url)
        return self._page_counts.get(domain, 0) >= self.max_per_domain

    def _record(self, url: str) -> None:
        domain = self._domain(url)
        self._page_counts[domain] = self._page_counts.get(domain, 0) + 1
        self._total += 1

    def parse(self, response: Response):
        # ── requests-lib fallback ────────────────────────────────────────────
        if response.meta.get("use_requests_fallback"):
            yield from self._requests_fallback(response.url, response.meta)
            return

        # ── skip signals ─────────────────────────────────────────────────────
        if response.meta.get("skip"):
            yield self._failed_item(
                response.url, "skip", response.meta.get("skip_reason", "all fallbacks exhausted")
            )
            return

        if response.meta.get("robots_blocked"):
            yield self._failed_item(response.url, "robots_blocked", "robots.txt")
            return

        if response.meta.get("auth_walled"):
            yield self._failed_item(response.url, "auth_walled", "auth wall detected")
            return

        # ── PDF ───────────────────────────────────────────────────────────────
        ct = response.headers.get("Content-Type", b"").decode("utf-8", errors="replace").lower()
        if any(t in ct for t in _PDF_CONTENT_TYPES) or response.url.lower().endswith(".pdf"):
            yield self._pdf_item(response)
            return

        # ── normal page ───────────────────────────────────────────────────────
        if self._over_limit(response.url):
            logger.debug("Page cap reached, skipping %s", response.url)
            return

        self._record(response.url)
        yield self._page_item(response)
        yield from self._extract_links(response)

    def _page_item(self, response: Response) -> dict:
        fallback = "playwright" if response.meta.get("playwright") else "http"
        if response.meta.get("use_requests_fallback"):
            fallback = "requests"

        return {
            "url": response.url,
            "normalized_url": response.url,
            "domain": self._domain(response.url),
            "status": "success",
            "http_status": response.status,
            "fallback_used": fallback,
            "raw_html": response.text,
            "title": self._extract_title(response),
            "description": self._extract_meta_description(response),
            "body_markdown": None,
            "word_count": len(response.text.split()),
            "language": None,
            "page_type": None,
            "include_in_output": 1,
            "error_message": None,
        }

    def _pdf_item(self, response: Response) -> dict:
        return {
            "url": response.url,
            "normalized_url": response.url,
            "domain": self._domain(response.url),
            "status": "success",
            "http_status": response.status,
            "fallback_used": "http",
            "raw_html": None,
            "title": response.url.split("/")[-1],
            "description": "PDF document",
            "body_markdown": None,
            "word_count": 0,
            "language": None,
            "page_type": "document",
            "include_in_output": 1,
            "error_message": None,
        }

    def _failed_item(self, url: str, status: str, reason: str) -> dict:
        return {
            "url": url,
            "normalized_url": url,
            "domain": self._domain(url),
            "status": status,
            "http_status": None,
            "fallback_used": None,
            "raw_html": None,
            "title": None,
            "description": None,
            "body_markdown": None,
            "word_count": 0,
            "language": None,
            "page_type": None,
            "include_in_output": 0,
            "error_message": reason,
        }

    def _extract_links(self, response: Response):
        seed_domain = self._domain(response.url)
        seen = set()

        for href in response.css("a::attr(href)").getall():
            url = urljoin(response.url, href).split("#")[0]
            if not url.startswith(("http://", "https://")):
                continue
            if url in seen:
                continue
            seen.add(url)

            link_domain = self._domain(url)
            if not self.follow_external and link_domain != seed_domain:
                continue
            if self._over_limit(url):
                continue

            yield Request(
                url,
                callback=self.parse,
                meta={"fallback_level": 0, "depth": response.meta.get("depth", 0) + 1},
                errback=self.errback,
            )

    def _requests_fallback(self, url: str, meta: dict):
        """Synchronous fallback — runs in the same thread (called from parse)."""
        logger.info("requests fallback for %s", url)
        try:
            resp = req_lib.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 LLMsCrawler/1.0"},
                allow_redirects=True,
            )
            resp.raise_for_status()
            fake = HtmlResponse(
                url=resp.url,
                status=resp.status_code,
                body=resp.content,
                encoding=resp.apparent_encoding or "utf-8",
            )
            fake.meta.update(meta)
            fake.meta["use_requests_fallback"] = False
            fake.meta["fallback_used_requests"] = True
            yield from self.parse(fake)
        except Exception as exc:
            logger.error("requests fallback failed for %s: %s", url, exc)
            yield self._failed_item(url, "failed", f"requests: {exc}")

    def errback(self, failure):
        url = failure.request.url
        logger.error("Request failed: %s — %s", url, failure.value)
        yield self._failed_item(url, "failed", str(failure.value))

    @staticmethod
    def _extract_title(response: Response) -> str | None:
        return (
            response.css('meta[property="og:title"]::attr(content)').get()
            or response.css("title::text").get()
            or response.css("h1::text").get()
        )

    @staticmethod
    def _extract_meta_description(response: Response) -> str | None:
        return (
            response.css('meta[property="og:description"]::attr(content)').get()
            or response.css('meta[name="description"]::attr(content)').get()
        )
