# 🕷️ LLMs Web Crawler — Day 1

A production-grade web crawler built with **Scrapy + Playwright** that crawls websites and stores clean, deduplicated content in a local SQLite database.

---

## 📁 Project Structure

```
day1/
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
│   │   ├── dedup_pipeline.py     # URL deduplication
│   │   └── storage_pipeline.py   # SQLite storage
│   ├── spiders/
│   │   ├── base_spider.py        # Base spider class
│   │   └── universal_spider.py   # Main crawl spider
│   └── settings.py               # Scrapy settings
├── storage/
│   ├── db.py                     # DB connection & queries
│   └── schema.sql                # SQLite schema
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

---

## ⚙️ Installation

```bash
cd day1
pip install -r requirements.txt

# Install Playwright browser (needed for JS rendering)
playwright install chromium
```

---

## 🧪 Usage

### Basic Crawl

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

Crawled data is saved to a **SQLite database** (`crawl.db` by default). The schema is defined in `storage/schema.sql`.

---

## 📦 Tech Stack

- [Scrapy](https://scrapy.org/) — crawling framework
- [Playwright](https://playwright.dev/python/) — headless browser for JS pages
- [SQLite](https://www.sqlite.org/) — local storage
- [PyYAML](https://pyyaml.org/) — configuration

---

## 📄 License

MIT
