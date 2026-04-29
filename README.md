# 🕷️ LLMs Web Crawler — Day 2

Builds on Day 1 by adding **content processing pipelines** and **`llms.txt` generation** — transforming raw crawled HTML into clean, structured content ready for LLM consumption.

---

## 📁 Project Structures

```
day2/
├── config/
│   ├── default.yaml              # Main crawler config
│   └── profiles/
│       ├── blog.yaml             # Profile for blog sites
│       └── docs_site.yaml        # Profile for documentation sites
├── crawler/
│   ├── extensions/
│   │   └── stats_extension.py    # Crawl stats tracking
│   ├── middlewares/
│   │   ├── playwright_middleware.py   # JS rendering fallback
│   │   ├── ratelimit_middleware.py    # Per-domain rate limiting
│   │   ├── retry_middleware.py        # Auto-retry on failure
│   │   └── robots_middleware.py       # robots.txt compliance
│   ├── pipelines/
│   │   ├── classify_pipeline.py  # Content classification  ⭐ NEW
│   │   ├── content_pipeline.py   # Content extraction      ⭐ NEW
│   │   ├── dedup_pipeline.py     # URL deduplication
│   │   └── storage_pipeline.py   # SQLite storage
│   ├── spiders/
│   │   ├── base_spider.py        # Base spider class
│   │   └── universal_spider.py   # Main crawl spider
│   └── settings.py               # Scrapy settings
├── processor/                    # ⭐ NEW
│   ├── classifier.py             # Page type classifier
│   ├── cleaner.py                # HTML cleaner
│   ├── extractor.py              # Content extractor
│   ├── llmstxt_builder.py        # llms.txt builder
│   └── pdf_extractor.py          # PDF content extraction
├── storage/
│   ├── db.py                     # DB connection & queries
│   └── schema.sql                # SQLite schema
├── generate_llmstxt.py           # ⭐ NEW — CLI to generate llms.txt
├── run_crawler.py                # CLI entry point
├── requirements.txt
└── scrapy.cfg
```

---

## 🚀 Features

- **Universal spider** — crawls any website with configurable depth and page limits
- **Playwright fallback** — automatically uses headless browser for JavaScript-heavy pages
- **Rate limiting** — respects per-domain request limits to avoid getting blocked
- **Auto-retry** — retries failed requests with backoff
- **robots.txt compliance** — obeys crawl rules by default
- **URL deduplication** — strips tracking params (UTM, fbclid, gclid, etc.)
- **SQLite storage** — saves compressed raw HTML locally
- **Content pipeline** — extracts clean text from raw HTML after crawling ⭐ NEW
- **Classify pipeline** — identifies page types (blog, docs, landing page, etc.) ⭐ NEW
- **PDF extraction** — pulls text content from PDF files found during crawl ⭐ NEW
- **llms.txt generator** — produces compact and full-content output files ⭐ NEW

---

## ⚙️ Installation

```bash
cd day2
pip install -r requirements.txt

# Install Playwright browser (needed for JS rendering)
playwright install chromium
```

---

## 🧪 Usage

### Step 1: Run the Crawler

```bash
python run_crawler.py --url https://example.com
```

### With Options

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

### Step 2: Generate llms.txt

```bash
# Generate both llms.txt and llms-full.txt
python generate_llmstxt.py --db crawl.db --out ./output

# Validate an existing llms.txt
python generate_llmstxt.py --db crawl.db --validate-only
```

This produces two files:

| File | Description |
|------|-------------|
| `llms.txt` | Compact index of all crawled pages (titles + URLs) |
| `llms-full.txt` | Full content of every crawled page for LLM ingestion |

---

## 🔧 Configuration

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

## 🗄️ Storage

Crawled and processed data is saved to a **SQLite database** (`crawl.db` by default). The schema is defined in `storage/schema.sql`.

```bash
python run_crawler.py --url https://example.com --db my_crawl.db
python generate_llmstxt.py --db my_crawl.db --out ./output
```

---

## 📦 Tech Stack

- [Scrapy](https://scrapy.org/) — crawling framework
- [Playwright](https://playwright.dev/python/) — headless browser for JS pages
- [SQLite](https://www.sqlite.org/) — local storage
- [PyYAML](https://pyyaml.org/) — configuration

---

## 📄 License

MIT
