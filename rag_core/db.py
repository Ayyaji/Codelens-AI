"""SQLite schema for sessions, JD cache, tests, and student profiles."""

import sqlite3
from contextlib import contextmanager

from rag_core.config import get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    query TEXT NOT NULL,
    agent_used TEXT NOT NULL,
    response_time REAL,
    timestamp TEXT NOT NULL,
    error_type TEXT,
    topic TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_student_time
    ON sessions (student_id, timestamp);

CREATE TABLE IF NOT EXISTS kb_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS job_descriptions (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    filename TEXT,
    raw_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jd_hash ON job_descriptions (content_hash);

CREATE TABLE IF NOT EXISTS jd_analysis (
    content_hash TEXT PRIMARY KEY,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_tests (
    jd_id TEXT PRIMARY KEY,
    cache_key TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tests_cache ON generated_tests (cache_key);

CREATE TABLE IF NOT EXISTS student_profile (
    student_id TEXT NOT NULL,
    jd_id TEXT NOT NULL DEFAULT '',
    weak_topics TEXT NOT NULL,
    mistake_patterns TEXT NOT NULL,
    last_score REAL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (student_id, jd_id)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def connection():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_session_columns(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "error_type" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN error_type TEXT")
    if "topic" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN topic TEXT")


def init_db() -> None:
    """Create tables used by the judgment layer and the JD modules."""
    with connection() as conn:
        conn.executescript(SCHEMA)
        _ensure_session_columns(conn)
