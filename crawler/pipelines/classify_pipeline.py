"""
Classifies each page by type after content extraction.
Writes page_type into the item.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from processor.classifier import classify

logger = logging.getLogger(__name__)


class ClassifyPipeline:

    def process_item(self, item, spider):
        if item.get("status") != "success":
            return item

        # Already classified (e.g. PDF set to "document")
        if item.get("page_type"):
            return item

        url = item.get("url", "")
        body = item.get("body_markdown", "") or ""
        html = item.get("raw_html", "") or ""

        try:
            item["page_type"] = classify(url, body, html)
        except Exception as exc:
            logger.error("ClassifyPipeline failed for %s: %s", url, exc)
            item["page_type"] = "other"

        return item
