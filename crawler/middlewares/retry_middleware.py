import re
import logging
from scrapy import signals
from scrapy.http import Request, Response

logger = logging.getLogger(__name__)

# Markers that indicate a JS-rendered SPA shell with no real content
_SPA_PATTERNS = [
    re.compile(r'<div\s+id=["\']root["\']>\s*</div>', re.I),
    re.compile(r'<div\s+id=["\']app["\']>\s*</div>', re.I),
    re.compile(r'<noscript>[^<]*enable javascript[^<]*</noscript>', re.I),
    re.compile(r'<noscript>[^<]*javascript required[^<]*</noscript>', re.I),
]

_RETRIABLE_STATUS = {500, 502, 503, 504, 408, 429}
_AUTH_WALL_PATTERNS = [
    re.compile(r'<input[^>]+type=["\']password["\']', re.I),
]
_AUTH_REDIRECT_PATHS = {"/login", "/signin", "/auth", "/sign-in", "/log-in"}


def _word_count(text: str) -> int:
    return len(text.split())


def _is_spa_shell(body: str, min_words: int) -> bool:
    if _word_count(body) < min_words:
        for pat in _SPA_PATTERNS:
            if pat.search(body):
                return True
    return False


def _is_auth_wall(response: Response) -> bool:
    from urllib.parse import urlparse
    path = urlparse(response.url).path.rstrip("/")
    if path in _AUTH_REDIRECT_PATHS:
        return True
    if response.status in (401, 403):
        return True
    body = response.text
    if _word_count(body) < 200:
        for pat in _AUTH_WALL_PATTERNS:
            if pat.search(body):
                return True
    return False


class FallbackRetryMiddleware:
    """
    Drives the fallback chain:
      0 → plain Scrapy HTTP
      1 → Playwright (JS render)
      2 → requests lib (sync, via meta flag — handled in spider)
      3 → SKIP

    Sets meta["fallback_level"] and meta["playwright"] accordingly.
    """

    FALLBACK_HTTP = 0
    FALLBACK_PLAYWRIGHT = 1
    FALLBACK_REQUESTS = 2
    FALLBACK_SKIP = 3

    def __init__(self, min_words: int):
        self.min_words = min_words

    @classmethod
    def from_crawler(cls, crawler):
        return cls(min_words=crawler.settings.getint("MIN_WORDS_FOR_HTTP", 50))

    def process_response(self, request, response, spider):
        level = request.meta.get("fallback_level", self.FALLBACK_HTTP)

        if response.status in _RETRIABLE_STATUS:
            return self._next_level(request, response, spider, level, f"HTTP {response.status}")

        if _is_auth_wall(response):
            request.meta["auth_walled"] = True
            logger.info("Auth wall detected: %s", request.url)
            return response  # let spider handle

        if level == self.FALLBACK_HTTP and _is_spa_shell(response.text, self.min_words):
            return self._next_level(request, response, spider, level, "SPA shell detected")

        return response

    def process_exception(self, request, exception, spider):
        level = request.meta.get("fallback_level", self.FALLBACK_HTTP)
        logger.warning("Exception at fallback level %d for %s: %s", level, request.url, exception)
        return self._next_level(request, None, spider, level, str(exception))

    def _next_level(self, request, response, spider, current_level: int, reason: str):
        next_level = current_level + 1

        if next_level >= self.FALLBACK_SKIP:
            logger.warning("All fallbacks exhausted for %s (%s) — skipping", request.url, reason)
            request.meta["skip"] = True
            request.meta["skip_reason"] = reason
            if response:
                return response
            # Return a dummy response so the pipeline can record the failure
            from scrapy.http import HtmlResponse
            return HtmlResponse(url=request.url, status=0, body=b"", encoding="utf-8")

        logger.info(
            "Fallback %d→%d for %s: %s",
            current_level, next_level, request.url, reason
        )

        new_request = request.copy()
        new_request.meta["fallback_level"] = next_level
        new_request.dont_filter = True

        if next_level == self.FALLBACK_PLAYWRIGHT:
            new_request.meta["playwright"] = True
            new_request.meta.pop("playwright_include_page", None)
        elif next_level == self.FALLBACK_REQUESTS:
            new_request.meta["playwright"] = False
            new_request.meta["use_requests_fallback"] = True

        return new_request
