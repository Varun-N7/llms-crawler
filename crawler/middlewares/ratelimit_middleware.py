import time
import logging
import tldextract
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Per-domain token bucket rate limiter.
    Respects Crawl-delay values written into meta by RobotsMiddleware.
    """

    def __init__(self, default_rps: float):
        self.default_rps = default_rps
        # domain → (tokens, last_refill_time)
        self._buckets: dict[str, list] = defaultdict(lambda: [1.0, time.monotonic()])
        # domain → override rps from robots Crawl-delay
        self._domain_rps: dict[str, float] = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            default_rps=crawler.settings.getfloat("RATE_LIMIT_PER_DOMAIN", 2.0)
        )

    def set_crawl_delay(self, domain: str, delay_seconds: float) -> None:
        """Called by RobotsMiddleware to override rate for a domain."""
        rps = 1.0 / delay_seconds if delay_seconds > 0 else self.default_rps
        effective = min(rps, self.default_rps)
        self._domain_rps[domain] = effective
        logger.debug("Rate for %s set to %.2f rps (crawl-delay=%.1fs)", domain, effective, delay_seconds)

    def process_request(self, request, spider):
        domain = tldextract.extract(request.url).registered_domain
        rps = self._domain_rps.get(domain, self.default_rps)
        bucket = self._buckets[domain]

        now = time.monotonic()
        elapsed = now - bucket[1]
        bucket[0] = min(1.0, bucket[0] + elapsed * rps)
        bucket[1] = now

        if bucket[0] >= 1.0:
            bucket[0] -= 1.0
            return None  # allow immediately

        wait = (1.0 - bucket[0]) / rps
        logger.debug("Rate limiting %s — sleeping %.2fs", domain, wait)
        time.sleep(wait)
        bucket[0] = 0.0
        bucket[1] = time.monotonic()
        return None
