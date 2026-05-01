# LLMs Web Crawler

A production-grade web crawler built with **Scrapy + Playwright** that crawls websites, processes content, generates `llms.txt` files, and provides a **live monitoring dashboard** for real-time visibility.

---

## Quick Start

```bash
pip install -r requirements.txt
playwright install chromium
python dashboard/app.py
python run_crawler.py --url https://example.com
python generate_llmstxt.py --db crawl.db --out ./output
```

---

## Prerequisites

- Python 3.8+
- pip
- Chromium (installed via Playwright)

---

## Dashboard Components

### `app.py` — Main Dashboard App
The entry point for the dashboard. Initializes and wires together all components, manages the overall layout, and starts the live update loop.

### `state.py` — State Management
Handles the global dashboard state — tracks crawl progress, page counts, active URLs, and export status across all components in real time.

### `live_monitor.py` — Live Crawl Monitor
Shows real-time crawl activity as it happens — displays pages being crawled, success/failure status, crawl speed, and progress towards the page limit.

### `url_table.py` — URL Table
A browsable table of all crawled URLs with metadata like page title, status code, word count, and content type. Supports filtering and sorting.

### `content_preview.py` — Content Preview
Click any URL in the table to preview the extracted clean text content for that page — useful for verifying crawl quality before generating `llms.txt`.

### `control_panel.py` — Control Panel
Start, stop, and configure crawls directly from the UI — set the seed URL, depth, page limit, and profile without touching the terminal.

### `export_panel.py` — Export Panel
Generate and download `llms.txt` and `llms-full.txt` directly from the dashboard with a single click once the crawl is complete.

---

## Features

- **Universal spider** — crawls any website with configurable depth and page limits
- **Playwright fallback** — automatically uses headless browser for JavaScript-heavy pages
- **Rate limiting** — respects per-domain request limits to avoid getting blocked
- **Auto-retry** — retries failed requests with backoff
- **robots.txt compliance** — obeys crawl rules by default
- **URL deduplication** — strips tracking params (UTM, fbclid, gclid, etc.)
- **SQLite storage** — saves compressed raw HTML locally
- **Content pipeline** — extracts clean text from raw HTML after crawling
- **Classify pipeline** — identifies page types (blog, docs, landing page, etc.)
- **PDF extraction** — pulls text content from PDF files found during crawl
- **llms.txt generator** — produces compact and full-content output files
- **Live dashboard** — real-time crawl monitoring with content preview and export

---

## Installation

```bash
pip install -r requirements.txt

# Install Playwright browser (needed for JS rendering)
playwright install chromium
```

---

## Usage

### Start the Dashboard

```bash
python dashboard/app.py
```

Then open your browser at **`http://localhost:8501`**

### Run the Crawler

```bash
python run_crawler.py --url https://example.com
```

```bash
# Custom depth and page limit
python run_crawler.py --url https://example.com --depth 3 --max-pages 200

# Multiple seed URLs
python run_crawler.py --url https://a.com,https://b.com

# Use a config profile
python run_crawler.py --url https://docs.example.com --profile docs_site

# Custom SQLite DB path
python run_crawler.py --url https://example.com --db my_crawl.db

# Disable Playwright (faster, skips JS rendering)
python run_crawler.py --url https://example.com --no-playwright
```

### Generate llms.txt

```bash
# From terminal
python generate_llmstxt.py --db crawl.db --out ./output

# Or use the Export Panel in the dashboard
```

### Output Example

```
# Example Site
> Documentation and guides for Example Site

## Getting Started
https://example.com/getting-started
A beginner's guide to getting started with Example Site.

## API Reference
https://example.com/api
Full API reference documentation.
```

---

## Configuration

Edit `config/default.yaml` to tune the crawler:

| Setting | Default | Description |
|---|---|---|
| `max_depth` | 3 | How deep to follow links |
| `max_pages` | 500 | Total page crawl limit |
| `max_pages_per_domain` | 100 | Per-domain cap |
| `concurrent_requests` | 16 | Global concurrency |
| `rate_limit_per_domain` | 2.0 req/s | Throttle per domain |
| `playwright.enabled` | true | JS rendering fallback |
| `robots.obey` | true | Respect robots.txt |
| `follow_external_links` | false | Stay on seed domain |
| `store_raw_html` | true | Save compressed HTML |

### Config Profiles

Use pre-built profiles from `config/profiles/`:

```bash
--profile blog        # For blog-style sites
--profile docs_site   # For documentation sites
```

---

## Tech Stack

- [Scrapy](https://scrapy.org/) — crawling framework
- [Playwright](https://playwright.dev/python/) — headless browser for JS pages
- [SQLite](https://www.sqlite.org/) — local storage
- [PyYAML](https://pyyaml.org/) — configuration
