import sqlite3
import zlib
import os
from pathlib import Path

DB_PATH = os.environ.get("CRAWLER_DB_PATH", "crawl.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: str = DB_PATH) -> None:
    conn = get_connection(path)
    with conn:
        conn.executescript(SCHEMA_PATH.read_text())
    conn.close()


def compress_html(html: str) -> bytes:
    return zlib.compress(html.encode("utf-8", errors="replace"))


def decompress_html(blob: bytes) -> str:
    return zlib.decompress(blob).decode("utf-8", errors="replace")


def insert_page(conn: sqlite3.Connection, data: dict) -> None:
    raw_html = data.get("raw_html")
    if isinstance(raw_html, str):
        raw_html = compress_html(raw_html)

    conn.execute(
        """
        INSERT OR REPLACE INTO pages
            (url, normalized_url, domain, status, http_status, fallback_used,
             page_type, title, description, body_markdown, raw_html,
             word_count, language, crawled_at, include_in_output, error_message)
        VALUES
            (:url, :normalized_url, :domain, :status, :http_status, :fallback_used,
             :page_type, :title, :description, :body_markdown, :raw_html,
             :word_count, :language, CURRENT_TIMESTAMP, :include_in_output, :error_message)
        """,
        {
            "url": data["url"],
            "normalized_url": data.get("normalized_url", data["url"]),
            "domain": data.get("domain", ""),
            "status": data.get("status", "success"),
            "http_status": data.get("http_status"),
            "fallback_used": data.get("fallback_used", "http"),
            "page_type": data.get("page_type"),
            "title": data.get("title"),
            "description": data.get("description"),
            "body_markdown": data.get("body_markdown"),
            "raw_html": raw_html,
            "word_count": data.get("word_count", 0),
            "language": data.get("language"),
            "include_in_output": data.get("include_in_output", 1),
            "error_message": data.get("error_message"),
        },
    )


def insert_log(conn: sqlite3.Connection, level: str, message: str, spider: str = "") -> None:
    conn.execute(
        "INSERT INTO logs (level, spider, message) VALUES (?, ?, ?)",
        (level, spider, message),
    )


def get_control_action(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT action FROM control ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["action"] if row else None


def clear_control(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM control")
