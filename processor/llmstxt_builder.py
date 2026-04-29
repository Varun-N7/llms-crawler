"""
Assembles llms.txt and llms-full.txt from crawled pages stored in SQLite.

llms.txt spec: https://llmstxt.org/
  - H1 site title
  - blockquote description
  - H2 sections
  - markdown links with one-line descriptions
  - "## Optional" marker separates essential from supplementary sections

llms-full.txt: same structure, each link followed by full page content inline.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from storage.db import get_connection

logger = logging.getLogger(__name__)

MAX_PAGE_WORDS = 10_000

# Section order and H2 headings — items before OPTIONAL_MARKER are "essential"
SECTION_ORDER = [
    "homepage",
    "docs",
    "api_reference",
    "guide",
    None,  # ← OPTIONAL_MARKER inserted here
    "blog",
    "changelog",
    "support",
    "about",
    "pricing",
    "legal",
    "document",
    "other",
]

SECTION_HEADINGS = {
    "homepage":      "Home",
    "docs":          "Documentation",
    "api_reference": "API Reference",
    "guide":         "Guides",
    "blog":          "Blog",
    "changelog":     "Changelog",
    "support":       "Support",
    "about":         "About",
    "pricing":       "Pricing",
    "legal":         "Legal",
    "document":      "Documents",
    "other":         "Pages",
}


@dataclass
class PageEntry:
    url: str
    title: str
    description: str
    page_type: str
    body_markdown: str
    word_count: int


def build(db_path: str, output_dir: str = ".") -> tuple[str, str]:
    """
    Read pages from DB, generate both files.
    Returns (llms_txt_content, llms_full_txt_content).
    """
    conn = get_connection(db_path)
    pages = _load_pages(conn)
    conn.close()

    if not pages:
        logger.warning("No pages found in DB for llms.txt generation")
        return "", ""

    site_title, site_description = _infer_site_meta(pages)
    grouped = _group_by_type(pages)

    llms_txt = _build_index(site_title, site_description, grouped)
    llms_full = _build_full(site_title, site_description, grouped)

    out = Path(output_dir)
    (out / "llms.txt").write_text(llms_txt, encoding="utf-8")
    (out / "llms-full.txt").write_text(llms_full, encoding="utf-8")

    errors = validate(llms_txt)
    if errors:
        logger.warning("llms.txt validation issues: %s", errors)
    else:
        logger.info("llms.txt generated and validated OK")

    logger.info("llms-full.txt generated (%d chars)", len(llms_full))
    return llms_txt, llms_full


def _load_pages(conn: sqlite3.Connection) -> list[PageEntry]:
    rows = conn.execute(
        """
        SELECT url, title, description, page_type, body_markdown, word_count
        FROM pages
        WHERE status = 'success'
          AND include_in_output = 1
          AND (body_markdown IS NOT NULL AND body_markdown != '')
        ORDER BY page_type, word_count DESC
        """
    ).fetchall()

    entries = []
    for row in rows:
        entries.append(PageEntry(
            url=row["url"],
            title=_clean_title(row["title"] or "", row["url"]),
            description=_clean_desc(row["description"] or "", row["body_markdown"] or ""),
            page_type=row["page_type"] or "other",
            body_markdown=row["body_markdown"] or "",
            word_count=row["word_count"] or 0,
        ))
    return entries


def _infer_site_meta(pages: list[PageEntry]) -> tuple[str, str]:
    # Homepage page as the source of site title/description
    for p in pages:
        if p.page_type == "homepage":
            return p.title or _domain_title(p.url), p.description or ""

    # Fallback: derive from the most common domain
    if pages:
        domain = urlparse(pages[0].url).netloc.lstrip("www.")
        return domain.replace(".", " ").title(), ""

    return "Site", ""


def _domain_title(url: str) -> str:
    netloc = urlparse(url).netloc.lstrip("www.")
    return netloc.split(".")[0].title()


def _group_by_type(pages: list[PageEntry]) -> dict[str, list[PageEntry]]:
    groups: dict[str, list[PageEntry]] = {}
    for page in pages:
        groups.setdefault(page.page_type, []).append(page)
    return groups


def _build_index(title: str, description: str, grouped: dict[str, list[PageEntry]]) -> str:
    lines = [f"# {title}", "", f"> {description}", ""]
    _append_sections(lines, grouped, full=False)
    return "\n".join(lines) + "\n"


def _build_full(title: str, description: str, grouped: dict[str, list[PageEntry]]) -> str:
    lines = [f"# {title}", "", f"> {description}", ""]
    _append_sections(lines, grouped, full=True)
    return "\n".join(lines) + "\n"


def _append_sections(lines: list[str], grouped: dict[str, list[PageEntry]], full: bool) -> None:
    optional_inserted = False

    for section_type in SECTION_ORDER:
        # Insert the Optional marker
        if section_type is None:
            if not optional_inserted:
                lines.append("## Optional")
                lines.append("")
                optional_inserted = True
            continue

        pages = grouped.get(section_type, [])
        if not pages:
            continue

        heading = SECTION_HEADINGS.get(section_type, section_type.title())
        lines.append(f"## {heading}")
        lines.append("")

        for page in pages:
            link_line = f"- [{page.title}]({page.url}): {page.description}"
            lines.append(link_line)

            if full:
                body = page.body_markdown
                words = body.split()
                truncated = False
                if len(words) > MAX_PAGE_WORDS:
                    body = " ".join(words[:MAX_PAGE_WORDS])
                    truncated = True
                lines.append("")
                lines.append("---")
                lines.append(body)
                if truncated:
                    lines.append("\n[truncated]")
                lines.append("---")
                lines.append("")

        lines.append("")


def validate(content: str) -> list[str]:
    """Returns a list of spec violation messages (empty = valid)."""
    errors = []
    lines = [l for l in content.splitlines() if l.strip()]

    if not lines:
        return ["File is empty"]

    if not lines[0].startswith("# "):
        errors.append(f"First line must be H1 title, got: {lines[0]!r}")

    if len(lines) < 2 or not lines[1].startswith("> "):
        errors.append("Second non-empty line must be a blockquote description")

    link_re = re.compile(r"^- \[.+\]\(.+\): .+")
    for i, line in enumerate(lines):
        if line.startswith("- ") and not link_re.match(line):
            errors.append(f"Line {i+1} has malformed link entry: {line!r}")

    return errors


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_title(title: str, url: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        # Derive from URL path
        path = urlparse(url).path.strip("/")
        title = path.split("/")[-1].replace("-", " ").replace("_", " ").title() or url
    return title[:120]


def _clean_desc(description: str, body: str) -> str:
    description = re.sub(r"\s+", " ", description).strip()
    if not description and body:
        # First sentence of body
        clean_body = re.sub(r"[#*`\[\]>]", "", body)
        match = re.search(r"[.!?]", clean_body[:300])
        end = match.end() if match else min(len(clean_body), 160)
        description = clean_body[:end].strip()
    return description[:200]
