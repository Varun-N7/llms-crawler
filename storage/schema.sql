PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    normalized_url TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    http_status INTEGER,
    fallback_used TEXT,
    page_type TEXT,
    title TEXT,
    description TEXT,
    body_markdown TEXT,
    raw_html BLOB,
    word_count INTEGER,
    language TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    include_in_output INTEGER DEFAULT 1,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS frontier (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending',
    depth INTEGER DEFAULT 0,
    discovered_from TEXT,
    priority INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crawl_sessions (
    id INTEGER PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    config_json TEXT,
    total_crawled INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    total_skipped INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    spider TEXT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS control (
    id INTEGER PRIMARY KEY,
    action TEXT,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pages_domain ON pages(domain);
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status);
CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier(status);
CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
