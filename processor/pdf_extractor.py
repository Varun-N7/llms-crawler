"""
PDF text extraction using pypdf.
Returns a PageData-compatible dict.
"""

from __future__ import annotations

import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def extract_pdf(content: bytes, url: str) -> dict:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(content))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())

        body = "\n\n".join(pages_text)
        title = url.split("/")[-1].replace(".pdf", "").replace("-", " ").replace("_", " ").title()

        info = reader.metadata or {}
        if info.get("/Title"):
            title = str(info["/Title"]).strip()

        return {
            "body_markdown": body,
            "title": title,
            "description": body[:160].replace("\n", " ").strip() if body else "",
            "word_count": len(body.split()),
            "page_type": "document",
            "extraction_method": "pypdf",
        }
    except Exception as exc:
        logger.warning("PDF extraction failed for %s: %s", url, exc)
        return {
            "body_markdown": "",
            "title": url.split("/")[-1],
            "description": "",
            "word_count": 0,
            "page_type": "document",
            "extraction_method": "failed",
            "error_message": str(exc),
        }
