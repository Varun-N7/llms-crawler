import hashlib
import logging
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

_STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
}


def normalize_url(url: str) -> str:
    parsed = urlparse(url.lower().rstrip("/"))
    clean_params = urlencode(
        [(k, v) for k, v in sorted(parse_qsl(parsed.query)) if k not in _STRIP_PARAMS]
    )
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, clean_params, ""  # strip fragment
    ))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


class DedupPipeline:
    def __init__(self):
        self._seen_urls: set[str] = set()
        self._seen_content: set[str] = set()

    def process_item(self, item, spider):
        url = item.get("url", "")
        norm = normalize_url(url)

        if norm in self._seen_urls:
            raise DropItem(f"Duplicate URL: {url}")
        self._seen_urls.add(norm)

        body = item.get("body_markdown") or item.get("raw_html") or ""
        if body:
            h = content_hash(body)
            if h in self._seen_content:
                raise DropItem(f"Duplicate content at: {url}")
            self._seen_content.add(h)

        item["normalized_url"] = norm
        return item
