"""
HTML → clean markdown extraction.

Primary:   trafilatura  (best article/doc extraction)
Fallback:  readability-lxml + html2text
Last resort: raw text stripped from BeautifulSoup
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy imports — heavy libs only loaded when first used
_trafilatura = None
_readability = None
_html2text = None
_bs4 = None


def _load_trafilatura():
    global _trafilatura
    if _trafilatura is None:
        import trafilatura
        _trafilatura = trafilatura
    return _trafilatura


def _load_readability():
    global _readability
    if _readability is None:
        from readability import Document
        _readability = Document
    return _readability


def _load_html2text():
    global _html2text
    if _html2text is None:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        _html2text = h
    return _html2text


def _load_bs4():
    global _bs4
    if _bs4 is None:
        from bs4 import BeautifulSoup
        _bs4 = BeautifulSoup
    return _bs4


@dataclass
class PageData:
    url: str
    title: str = ""
    description: str = ""
    body_markdown: str = ""
    word_count: int = 0
    page_type: str = ""
    language: str = ""
    links: list[str] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    extraction_method: str = ""


def extract(html: str, url: str) -> PageData:
    """
    Extract clean markdown text from raw HTML.
    Tries trafilatura → readability → bs4 strip.
    """
    if not html or not html.strip():
        return PageData(url=url, extraction_method="empty")

    # ── Stage 1: trafilatura ──────────────────────────────────────────────────
    try:
        traf = _load_trafilatura()
        result = traf.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            output_format="markdown",
            favor_precision=False,
            favor_recall=True,
        )
        if result and len(result.split()) >= 50:
            metadata = traf.extract_metadata(html, default_url=url)
            return PageData(
                url=url,
                title=_clean(getattr(metadata, "title", "") or ""),
                description=_clean(getattr(metadata, "description", "") or ""),
                body_markdown=result,
                word_count=len(result.split()),
                language=getattr(metadata, "language", "") or "",
                links=_extract_links(html, url),
                extraction_method="trafilatura",
            )
    except Exception as exc:
        logger.debug("trafilatura failed for %s: %s", url, exc)

    # ── Stage 2: readability + html2text ─────────────────────────────────────
    try:
        Document = _load_readability()
        doc = Document(html)
        article_html = doc.summary(html_partial=True)
        h2t = _load_html2text()
        markdown = h2t.handle(article_html)
        if markdown and len(markdown.split()) >= 30:
            return PageData(
                url=url,
                title=_clean(doc.title() or ""),
                description=_first_sentence(markdown),
                body_markdown=markdown,
                word_count=len(markdown.split()),
                links=_extract_links(html, url),
                extraction_method="readability",
            )
    except Exception as exc:
        logger.debug("readability failed for %s: %s", url, exc)

    # ── Stage 3: raw BS4 text strip ──────────────────────────────────────────
    try:
        BS4 = _load_bs4()
        soup = BS4(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        title = soup.find("title")
        return PageData(
            url=url,
            title=_clean(title.get_text() if title else ""),
            description=_first_sentence(text),
            body_markdown=text,
            word_count=len(text.split()),
            links=_extract_links(html, url),
            extraction_method="bs4_strip",
        )
    except Exception as exc:
        logger.warning("All extraction methods failed for %s: %s", url, exc)
        return PageData(url=url, extraction_method="failed")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _first_sentence(text: str, max_chars: int = 160) -> str:
    text = _clean(text)
    match = re.search(r"[.!?]", text[:300])
    end = match.end() if match else min(len(text), max_chars)
    return text[:end].strip()


def _extract_links(html: str, base_url: str) -> list[str]:
    try:
        from urllib.parse import urljoin
        BS4 = _load_bs4()
        soup = BS4(html, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].split("#")[0].strip()
            if not href:
                continue
            full = urljoin(base_url, href)
            if full.startswith(("http://", "https://")):
                links.append(full)
        return list(dict.fromkeys(links))  # deduplicate preserving order
    except Exception:
        return []
