"""
SQLite persistence layer for the CSI Visit Tracking System.
Plain sqlite3 (no ORM) — small-agency internal tool, keep dependencies light.
"""
import os
import sqlite3
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CSI_DB", os.path.join(HERE, "data", "csi_visit_tracker.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS consumers (
    id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    name TEXT,
    worker_code TEXT,          -- who is assigned to visit this consumer (was "WSC")
    area TEXT,                 -- SOUTHERS | SOUTHEAST | CENTRAL | UNCLASSIFIED
    address TEXT,
    city TEXT,
    zip TEXT,
    phone TEXT,
    health_manager TEXT,
    effective_date TEXT,
    active INTEGER DEFAULT 1,
    gh INTEGER DEFAULT 0,
    il INTEGER DEFAULT 0,
    cdc INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'worker',   -- 'manager' | 'worker'
    worker_code TEXT,                       -- for role='worker': links to consumers.worker_code
    created_at TEXT,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS visit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumer_id INTEGER NOT NULL,
    visit_type TEXT NOT NULL,           -- 'sp' | 'quarterly' | 'monthly'
    due_year INTEGER NOT NULL,
    due_month INTEGER NOT NULL,         -- 1-12
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'completed'
    completed_date TEXT,
    note TEXT,
    submitted_by INTEGER,               -- users.id
    updated_at TEXT,
    UNIQUE(consumer_id, visit_type, due_year, due_month)
);

CREATE TABLE IF NOT EXISTS data_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    uploaded_at TEXT,
    uploaded_by INTEGER,
    row_count INTEGER
);

CREATE TABLE IF NOT EXISTS worker_directory (
    worker_code TEXT PRIMARY KEY,
    display_name TEXT,
    email TEXT,
    phone TEXT
);
"""


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def conn_ctx():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
