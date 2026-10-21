"""SQLite history can be copied into Mongo once, and a second run does not duplicate it."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from rag_core.judgment import get_student_context, judge_response_level
from rag_core.migrate_sqlite import migrate_sqlite
from rag_core.mongo import get_db

SCHEMA = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    query TEXT NOT NULL,
    agent_used TEXT NOT NULL,
    response_time REAL,
    timestamp TEXT NOT NULL,
    error_type TEXT,
    topic TEXT
);
CREATE TABLE kb_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
);
CREATE TABLE job_descriptions (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    filename TEXT,
    raw_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE jd_analysis (
    content_hash TEXT PRIMARY KEY,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE generated_tests (
    jd_id TEXT PRIMARY KEY,
    cache_key TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE student_profile (
    student_id TEXT NOT NULL,
    jd_id TEXT NOT NULL DEFAULT '',
    weak_topics TEXT NOT NULL,
    mistake_patterns TEXT NOT NULL,
    last_score REAL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (student_id, jd_id)
);
"""


def _sqlite(path):
    now = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(tzinfo=None).isoformat()
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO sessions (student_id, query, agent_used, response_time, timestamp, error_type, topic) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("s1", "NameError: x", "debug", 0.2, now, "NameError", None),
    )
    conn.execute(
        "INSERT INTO job_descriptions (id, content_hash, filename, raw_text, created_at) VALUES (?, ?, ?, ?, ?)",
        ("jd1", "abc", "role.txt", "Python and SQL", now),
    )
    conn.execute(
        "INSERT INTO jd_analysis (content_hash, analysis_json, created_at) VALUES (?, ?, ?)",
        ("abc", json.dumps({"skills": [], "roadmap": []}), now),
    )
    conn.execute(
        "INSERT INTO generated_tests (jd_id, cache_key, questions_json, created_at) VALUES (?, ?, ?, ?)",
        ("jd1", "cache", json.dumps([{"id": "q1"}]), now),
    )
    conn.execute(
        "INSERT INTO student_profile (student_id, jd_id, weak_topics, mistake_patterns, last_score, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("s1", "jd1", json.dumps(["SQL"]), json.dumps(["concept_gap:SQL"]), 40, now),
    )
    conn.execute(
        "INSERT INTO kb_pending (query, content, source, timestamp, status) VALUES (?, ?, ?, ?, ?)",
        ("What is WAL?", "write ahead log", "https://example.com", now, "pending"),
    )
    conn.commit()
    conn.close()


async def test_sqlite_rows_become_a_student_who_can_log_in(client, tmp_path):
    path = tmp_path / "codelens.db"
    _sqlite(path)
    first = await migrate_sqlite(str(path))
    assert first["users"] == 1
    assert first["chats"] == 1
    creds = first["credentials"][0]

    login = await client.post(
        "/auth/login",
        json={"email": creds["email"], "password": creds["password"]},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    assert login.json()["user"]["role"] == "student"

    persona = await client.get("/me/persona", headers=headers)
    assert persona.json()["weak_topics"] == ["SQL"]
    assert persona.json()["mistake_patterns"] == ["concept_gap:SQL"]
    assert persona.json()["jds"][0]["jd_id"] == "jd1"
    history = await client.get("/me/history", headers=headers)
    assert history.json()["jds"][0]["filename"] == "role.txt"

    context = await get_student_context(creds["user_id"])
    assert judge_response_level("NameError again", "concept", context) == "hint"

    second = await migrate_sqlite(str(path))
    assert second["users"] == 0
    assert second["credentials"] == []
    db = await get_db()
    assert await db.chats.count_documents({"user_id": creds["user_id"]}) == 1
    assert await db.kb_pending.count_documents({"status": "pending"}) == 1
