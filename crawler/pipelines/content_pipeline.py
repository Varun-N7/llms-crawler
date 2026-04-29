"""
Runs HTML through the extraction + cleaning pipeline.
Populates: body_markdown, title, description, word_count, language, extraction_method.
"""

import logging
import sys
from pathlib import Path

# Ensure project root is importable when running under Scrapy
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from processor.extractor import extract
from processor.cleaner import clean, is_thin, clean_links
from processor.pdf_extractor import extract_pdf

logger = logging.getLogger(__name__)


class ContentPipeline:

    def process_item(self, item, spider):
        url = item.get("url", "")
        status = item.get("status", "")

        # Only process successful pages
        if status != "success":
            return item

        # PDF pages: content extracted separately
        if item.get("page_type") == "document":
            return item

        raw_html = item.get("raw_html")
        if not raw_html:
            return item

        # If it looks like a PDF response body
        if url.lower().endswith(".pdf") or (
            isinstance(raw_html, bytes) and raw_html[:4] == b"%PDF"
        ):
            pdf_data = extract_pdf(
                raw_html if isinstance(raw_html, bytes) else raw_html.encode(),
                url
            )
            item.update(pdf_data)
            return item

        try:
            page_data = extract(raw_html, url)

            # Prefer already-set title/description from spider's og: extraction
            # only fill in if blank
            if not item.get("title"):
                item["title"] = page_data.title
            if not item.get("description"):
                item["description"] = page_data.description

            body = clean(page_data.body_markdown)
            item["body_markdown"] = body
            item["word_count"] = len(body.split())
            item["language"] = page_data.language or item.get("language")

            if is_thin(body):
                logger.debug("Thin content at %s (%d words)", url, item["word_count"])

        except Exception as exc:
            logger.error("ContentPipeline failed for %s: %s", url, exc)

        return item
