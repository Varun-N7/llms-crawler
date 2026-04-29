"""
Post-extraction text cleanup.
- Strips residual boilerplate patterns
- Normalizes whitespace and punctuation
- Detects thin content
- Strips tracking params from extracted links
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid", "_hsenc", "_hsmi",
}

# Boilerplate line patterns to strip from extracted markdown
_BOILERPLATE_PATTERNS = [
    re.compile(r"^(accept|reject)\s+all\s+cookies?", re.I),
    re.compile(r"^we use cookies", re.I),
    re.compile(r"^(subscribe|sign up)\s+(to|for)\s+(our\s+)?newsletter", re.I),
    re.compile(r"^(all rights reserved|copyright\s+©)", re.I),
    re.compile(r"^skip\s+to\s+(main\s+)?content", re.I),
    re.compile(r"^(back to top|scroll to top)", re.I),
    re.compile(r"^\s*\|\s*$"),  # lone pipe separators
    re.compile(r"^(home\s*›|breadcrumb)", re.I),
    re.compile(r"^(share\s+this|share\s+on\s+(twitter|facebook|linkedin))", re.I),
    re.compile(r"^\d+\s+min\s+read$", re.I),
]

_WHITESPACE_RE = re.compile(r"\n{3,}")
_ZERO_WIDTH_RE = re.compile(r"[​‌‍﻿­]")
_SMART_QUOTES = str.maketrans({
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "–": "-", "—": "--",
    "…": "...",
})

THIN_CONTENT_THRESHOLD = 150  # words


def clean(text: str) -> str:
    if not text:
        return ""

    # Zero-width and smart punctuation
    text = _ZERO_WIDTH_RE.sub("", text)
    text = text.translate(_SMART_QUOTES)

    # Process line by line — remove boilerplate
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if any(pat.search(stripped) for pat in _BOILERPLATE_PATTERNS):
            continue
        cleaned.append(line)

    text = "\n".join(cleaned)
    text = _WHITESPACE_RE.sub("\n\n", text).strip()
    return text


def is_thin(text: str) -> bool:
    return len(text.split()) < THIN_CONTENT_THRESHOLD


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    clean_params = urlencode([
        (k, v) for k, v in parse_qsl(parsed.query)
        if k.lower() not in _TRACKING_PARAMS
    ])
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, clean_params, ""
    ))


def clean_links(links: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for link in links:
        cleaned = clean_url(link)
        if cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
