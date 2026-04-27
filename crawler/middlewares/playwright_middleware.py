import tldextract
from scrapy_playwright.page import PageMethod


class PlaywrightFallbackMiddleware:
    """
    Activates Playwright on a request only when:
    - meta["playwright"] is already True (set by FallbackRetryMiddleware), OR
    - the domain is in PLAYWRIGHT_FORCED_DOMAINS settings list.

    Never activates by default to keep costs low.
    """

    def __init__(self, forced_domains: list[str]):
        self.forced_domains = set(forced_domains)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            forced_domains=crawler.settings.getlist("PLAYWRIGHT_FORCED_DOMAINS", [])
        )

    def process_request(self, request, spider):
        domain = tldextract.extract(request.url).registered_domain

        if request.meta.get("playwright") or domain in self.forced_domains:
            request.meta["playwright"] = True
            # Release the page immediately after response — don't hold browser resources
            request.meta.setdefault("playwright_include_page", False)
            request.meta.setdefault(
                "playwright_page_methods",
                [PageMethod("wait_for_load_state", "networkidle")],
            )

        return None  # pass through; handler decides based on meta["playwright"]
