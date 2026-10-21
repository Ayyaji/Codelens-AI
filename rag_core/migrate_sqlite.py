"""Copy a legacy SQLite ``codelens.db`` into MongoDB.

SQLite had no passwords and no owner on a job description. Each distinct
``student_id`` becomes a student. The temporary password is printed once.
Job descriptions are attached to the first student who had a profile for them.

Already-migrated students (matched on ``legacy_student_id``) are left alone,
so the command can be run again.

    python -m rag_core.migrate_sqlite
    python -m rag_core.migrate_sqlite --sqlite codelens.db
"""

import argparse
import asyncio
import json
import re
import secrets
import sqlite3
import sys
from datetime import datetime, timezone

from rag_core.auth import hash_password
from rag_core.config import get_db_path
from rag_core.mongo import close_mongo, utcnow
from rag_core.store import (
    create_user,
    find_user_by_legacy,
    insert_kb,
    remember_jd,
    save_test,
)

LEGACY_SCHEMA_TABLES = (
    "sessions",
    "kb_pending",
    "job_descriptions",
    "jd_analysis",
    "generated_tests",
    "student_profile",
)


def _parse_ts(value) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if not value:
        return utcnow()
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return utcnow()
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _loads(value, fallback):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _email_for(student_id: str, taken: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9._+-]", "_", student_id.strip().lower())
    slug = slug.strip("._")[:40] or "student"
    email = f"{slug}@migrated.codelens.local"
    number = 2
    while email in taken:
        email = f"{slug}.{number}@migrated.codelens.local"
        number += 1
    taken.add(email)
    return email


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _read_sqlite(path: str) -> dict:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    present = _tables(conn)
    data = {name: [] for name in LEGACY_SCHEMA_TABLES}
    for name in LEGACY_SCHEMA_TABLES:
        if name not in present:
            continue
        data[name] = [dict(row) for row in conn.execute(f"SELECT * FROM {name}").fetchall()]
    conn.close()
    return data


async def migrate_sqlite(path: str | None = None) -> dict:
    """Load ``path`` (or ``CODELENS_DB``) into the configured Mongo database."""
    from rag_core.mongo import get_db

    sqlite_path = path or get_db_path()
    try:
        legacy = _read_sqlite(sqlite_path)
    except sqlite3.Error as exc:
        raise ValueError(f"Could not read {sqlite_path}: {exc}") from exc

    db = await get_db()
    student_ids = []
    seen = set()
    for row in legacy["sessions"] + legacy["student_profile"]:
        student_id = str(row.get("student_id") or "").strip()
        if student_id and student_id not in seen:
            seen.add(student_id)
            student_ids.append(student_id)

    taken = set()
    async for doc in db.users.find({}, {"email": 1}):
        if doc.get("email"):
            taken.add(doc["email"])

    credentials = []
    users_created = 0
    id_map: dict[str, str] = {}

    for student_id in student_ids:
        existing = await find_user_by_legacy(student_id)
        if existing is not None:
            id_map[student_id] = str(existing["_id"])
            continue
        email = _email_for(student_id, taken)
        password = secrets.token_urlsafe(9)
        user = await create_user(
            student_id[:80],
            email,
            await hash_password(password),
            role="student",
            legacy_student_id=student_id,
        )
        id_map[student_id] = str(user["_id"])
        users_created += 1
        credentials.append(
            {"legacy_student_id": student_id, "email": email, "password": password, "user_id": id_map[student_id]}
        )

    chats = 0
    activity = 0
    for student_id, user_id in id_map.items():
        if any(item["legacy_student_id"] == student_id for item in credentials):
            rows = [row for row in legacy["sessions"] if str(row.get("student_id")) == student_id]
            rows.sort(key=lambda row: str(row.get("timestamp") or ""))
            if rows:
                messages = []
                for row in rows:
                    when = _parse_ts(row.get("timestamp"))
                    messages.append(
                        {
                            "role": "user",
                            "content": row.get("query") or "",
                            "directive": None,
                            "agent_used": row.get("agent_used"),
                            "ts": when,
                        }
                    )
                    await db.activity.insert_one(
                        {
                            "user_id": user_id,
                            "type": "ask",
                            "detail": {
                                "query": row.get("query") or "",
                                "agent_used": row.get("agent_used"),
                                "response_time": row.get("response_time"),
                                "error_type": row.get("error_type"),
                                "topic": row.get("topic"),
                                "directive": None,
                            },
                            "ts": when,
                        }
                    )
                    activity += 1
                await db.chats.insert_one(
                    {
                        "user_id": user_id,
                        "title": "Migrated history",
                        "messages": messages,
                        "created_at": messages[0]["ts"],
                        "updated_at": messages[-1]["ts"],
                        "migrated": True,
                    }
                )
                chats += 1

            profiles = [row for row in legacy["student_profile"] if str(row.get("student_id")) == student_id]
            profiles.sort(key=lambda row: str(row.get("updated_at") or ""))
            if profiles:
                latest = profiles[-1]
                jd_ids = []
                scores = []
                for row in profiles:
                    jd_id = str(row.get("jd_id") or "")
                    if jd_id and jd_id not in jd_ids:
                        jd_ids.append(jd_id)
                    if row.get("last_score") is not None:
                        scores.append(
                            {
                                "test_id": f"legacy-{jd_id or 'score'}",
                                "score": float(row["last_score"]),
                                "created_at": _parse_ts(row.get("updated_at")),
                            }
                        )
                await db.personas.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "weak_topics": _loads(latest.get("weak_topics"), []),
                            "mistake_patterns": _loads(latest.get("mistake_patterns"), []),
                            "scores": scores[-200:],
                            "jd_ids": jd_ids,
                            "learning_notes": ["Migrated from SQLite."],
                            "updated_at": _parse_ts(latest.get("updated_at")),
                        }
                    },
                    upsert=True,
                )

    owner_for_jd: dict[str, str] = {}
    for row in legacy["student_profile"]:
        jd_id = str(row.get("jd_id") or "")
        student_id = str(row.get("student_id") or "")
        if jd_id and student_id in id_map and jd_id not in owner_for_jd:
            owner_for_jd[jd_id] = id_map[student_id]

    analyses = {row.get("content_hash"): _loads(row.get("analysis_json"), None) for row in legacy["jd_analysis"]}
    jds = 0
    for row in legacy["job_descriptions"]:
        jd_id = str(row["id"])
        owner = owner_for_jd.get(jd_id)
        doc = {
            "user_id": owner,
            "content_hash": row.get("content_hash"),
            "filename": row.get("filename") or "jd.txt",
            "raw_text": row.get("raw_text") or "",
            "analysis": analyses.get(row.get("content_hash")),
            "created_at": _parse_ts(row.get("created_at")),
        }
        result = await db.jds.update_one({"_id": jd_id}, {"$setOnInsert": doc}, upsert=True)
        if result.upserted_id is not None:
            jds += 1
            if owner:
                await remember_jd(owner, jd_id)

    tests = 0
    for row in legacy["generated_tests"]:
        jd_id = str(row["jd_id"])
        owner = owner_for_jd.get(jd_id)
        if owner is None:
            continue
        before = await db.tests.find_one({"jd_id": jd_id}, {"_id": 1})
        await save_test(jd_id, owner, row.get("cache_key") or "", _loads(row.get("questions_json"), []))
        if before is None:
            tests += 1

    kb = 0
    for row in legacy["kb_pending"]:
        status = row.get("status") or "pending"
        if status not in {"pending", "approved", "rejected"}:
            status = "pending"
        existing = await db.kb_pending.find_one({"legacy_id": row.get("id")})
        if existing is not None:
            continue
        when = _parse_ts(row.get("timestamp"))
        await insert_kb(
            content=row.get("content") or "",
            source=row.get("source"),
            proposed_by=None,
            query=row.get("query"),
            status=status,
            legacy_id=row.get("id"),
            reviewed_by=None,
            reviewed_at=None if status == "pending" else when,
            created_at=when,
        )
        kb += 1

    return {
        "users": users_created,
        "chats": chats,
        "activity": activity,
        "jds": jds,
        "tests": tests,
        "kb_pending": kb,
        "credentials": credentials,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy a CodeLens SQLite file into MongoDB")
    parser.add_argument("--sqlite", default=None, help="Path to codelens.db (default: CODELENS_DB or ./codelens.db)")
    args = parser.parse_args(argv)

    async def _run():
        try:
            return await migrate_sqlite(args.sqlite)
        finally:
            await close_mongo()

    try:
        result = asyncio.run(_run())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(
        "Migrated "
        f"{result['users']} users, {result['chats']} chats, {result['jds']} job descriptions, "
        f"{result['tests']} tests, {result['kb_pending']} knowledge-base items."
    )
    for item in result["credentials"]:
        print(f"  {item['legacy_student_id']} -> {item['email']} temporary password: {item['password']}")
    if result["credentials"]:
        print("These passwords are shown once. There is no password-reset endpoint yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
