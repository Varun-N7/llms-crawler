"""
Page type classifier.

Priority: URL pattern rules → structural heuristics → JSON-LD schema → fallback.

Page types:
    homepage, docs, api_reference, blog, guide, about,
    changelog, support, pricing, legal, document (PDF), other
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── URL pattern rules (first match wins) ─────────────────────────────────────

_URL_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"/(docs?|documentation|reference|manual|handbook)(/|$)", re.I), "docs"),
    (re.compile(r"/(api|sdk|rest|graphql|openapi)(-?reference)?(/|$)", re.I), "api_reference"),
    (re.compile(r"/(guides?|tutorials?|how-?to|getting-?started|quickstart)(/|$)", re.I), "guide"),
    (re.compile(r"/(blog|posts?|articles?|news|insights|updates?)(/|$)", re.I), "blog"),
    (re.compile(r"/(changelog|release-?notes?|whats?-?new|versions?)(/|$)", re.I), "changelog"),
    (re.compile(r"/(faq|support|help|kb|knowledge-?base|community)(/|$)", re.I), "support"),
    (re.compile(r"/(about|about-?us|company|team|mission|story)(/|$)", re.I), "about"),
    (re.compile(r"/pricing(/|$)", re.I), "pricing"),
    (re.compile(r"/(legal|terms|privacy|cookies?|gdpr|tos|license)(/|$)", re.I), "legal"),
]

# Structural heuristics applied to markdown body
_CODE_RE = re.compile(r"```")
_HTTP_METHOD_RE = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH|OPTIONS)\b")
_DATE_RE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4}\b", re.I)

# JSON-LD type → page type mapping
_JSONLD_MAP = {
    "article": "blog",
    "blogposting": "blog",
    "newsarticle": "blog",
    "technicalarticle": "docs",
    "faqpage": "support",
    "howto": "guide",
    "softwareapplication": "docs",
}


def classify(url: str, body_markdown: str, html: str = "") -> str:
    path = urlparse(url).path

    # Root path → homepage
    if path in ("", "/", "/index.html", "/index.htm"):
        return "homepage"

    # URL pattern rules
    for pattern, page_type in _URL_RULES:
        if pattern.search(path):
            return page_type

    # JSON-LD schema.org type
    if html:
        jsonld_type = _extract_jsonld_type(html)
        if jsonld_type and jsonld_type in _JSONLD_MAP:
            return _JSONLD_MAP[jsonld_type]

    # Structural heuristics on body text
    if body_markdown:
        return _structural_classify(body_markdown)

    return "other"


def _structural_classify(text: str) -> str:
    code_blocks = len(_CODE_RE.findall(text))
    http_methods = len(_HTTP_METHOD_RE.findall(text))
    has_date = bool(_DATE_RE.search(text[:500]))
    word_count = len(text.split())

    # Heavy code + HTTP methods → API reference
    if code_blocks >= 3 and http_methods >= 2:
        return "api_reference"

    # Code present but no HTTP methods → docs
    if code_blocks >= 2:
        return "docs"

    # Date in first 500 chars → blog post
    if has_date:
        return "blog"

    return "other"


def _extract_jsonld_type(html: str) -> str | None:
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.S | re.I
    )
    for raw in matches:
        try:
            data = json.loads(raw.strip())
            if isinstance(data, list):
                data = data[0]
            schema_type = data.get("@type", "")
            if isinstance(schema_type, list):
                schema_type = schema_type[0]
            return schema_type.lower()
        except Exception:
            continue
    return None
