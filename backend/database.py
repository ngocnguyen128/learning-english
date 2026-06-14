"""Lớp truy cập SQLite mỏng — không cần ORM cho app nhỏ này."""
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "vocab.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS words (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    word                TEXT NOT NULL,
    meaning             TEXT NOT NULL DEFAULT '',
    phonetic            TEXT NOT NULL DEFAULT '',
    part_of_speech      TEXT NOT NULL DEFAULT '',
    example             TEXT NOT NULL DEFAULT '',
    example_vi          TEXT NOT NULL DEFAULT '',
    known               INTEGER NOT NULL DEFAULT 0,   -- 1 = đã thuộc, bỏ qua khỏi ôn
    -- Các trường cho thuật toán SRS (SM-2)
    ease_factor         REAL NOT NULL DEFAULT 2.5,
    interval            INTEGER NOT NULL DEFAULT 0,   -- số ngày tới lần ôn kế
    repetitions         INTEGER NOT NULL DEFAULT 0,   -- số lần trả lời đúng liên tiếp
    due_date            TEXT NOT NULL DEFAULT (date('now')),
    last_reviewed       TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_due_date ON words(due_date);

-- Lưu trạng thái chung dạng key-value (vd: ngày sinh từ gần nhất)
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Nhật ký mỗi lần ôn (để thống kê tốc độ học)
CREATE TABLE IF NOT EXISTS review_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id     INTEGER NOT NULL,
    quality     INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL          -- giờ Việt Nam, dạng 'YYYY-MM-DD HH:MM:SS'
);

CREATE INDEX IF NOT EXISTS idx_log_date ON review_log(reviewed_at);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migration: thêm cột 'known' cho DB cũ chưa có
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(words)").fetchall()]
        if "known" not in cols:
            conn.execute("ALTER TABLE words ADD COLUMN known INTEGER NOT NULL DEFAULT 0")


def get_meta(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # cho phép truy cập theo tên cột
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
