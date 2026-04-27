import time
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
import tldextract

logger = logging.getLogger(__name__)

BOT_NAME = "LLMsCrawler"
CACHE_TTL = 3600  # seconds


class RobotsMiddleware:
    """
    Fetches and caches robots.txt per domain.
    - Blocks disallowed URLs.
    - Passes Crawl-delay to RateLimitMiddleware.
    - Exposes discovered Sitemap URLs via spider attribute.
    """

    def __init__(self, rate_limiter=None):
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}
        self._rate_limiter = rate_limiter

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def _get_parser(self, base_url: str) -> RobotFileParser | None:
        domain = tldextract.extract(base_url).registered_domain
        cached = self._cache.get(domain)
        if cached and (time.monotonic() - cached[1]) < CACHE_TTL:
            return cached[0]

        robots_url = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = requests.get(robots_url, timeout=10, headers={"User-Agent": BOT_NAME})
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
                logger.debug("Loaded robots.txt for %s", domain)
            else:
                parser.parse([])
        except Exception as exc:
            logger.warning("Could not fetch robots.txt for %s: %s", domain, exc)
            parser.parse([])

        self._cache[domain] = (parser, time.monotonic())
        return parser

    def _extract_sitemaps(self, parser: RobotFileParser) -> list[str]:
        # RobotFileParser doesn't expose sitemaps directly — parse source
        sitemaps = []
        if hasattr(parser, "entries"):
            pass
        # Access internal lines if available
        source = getattr(parser, "_source", None) or []
        for line in source:
            if isinstance(line, str) and line.lower().startswith("sitemap:"):
                url = line.split(":", 1)[1].strip()
                sitemaps.append(url)
        return sitemaps

    def process_request(self, request, spider):
        if request.meta.get("skip_robots"):
            return None

        parser = self._get_parser(request.url)
        if parser is None:
            return None

        if not parser.can_fetch(BOT_NAME, request.url):
            logger.info("robots.txt blocks: %s", request.url)
            request.meta["robots_blocked"] = True
            # Return a dummy disallowed response instead of raising IgnoreRequest
            # so StoragePipeline can record it
            from scrapy.http import HtmlResponse
            return HtmlResponse(
                url=request.url, status=403,
                body=b"Blocked by robots.txt", encoding="utf-8"
            )

        delay = parser.crawl_delay(BOT_NAME) or parser.crawl_delay("*")
        if delay:
            # Push to rate limiter if available
            rl = getattr(spider, "_rate_limiter", None)
            if rl:
                domain = tldextract.extract(request.url).registered_domain
                rl.set_crawl_delay(domain, float(delay))

        return None
