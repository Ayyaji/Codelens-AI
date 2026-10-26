"""Async MongoDB access for CodeLens.

Chroma still holds the debugging vectors. Everything else — accounts, chats,
personas, job descriptions, tests, submissions, the approval queue, and the
activity the judgment layer reads — lives here.

Timestamps are naive UTC. JSON responses append a ``Z``.
"""

import logging
import os
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger("codelens.mongo")

_client = None
_db = None
_owns_client = False
_indexes_ready = False


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_naive(value):
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def iso(value) -> str | None:
    """UTC timestamp with a Z suffix, or None when the value is missing."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, datetime):
        return str(value)
    return as_naive(value).isoformat(timespec="seconds") + "Z"


def as_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def set_database(database) -> None:
    """Point the process at a database. Tests and the smoke script use this."""
    global _db, _indexes_ready, _owns_client
    _db = database
    _indexes_ready = False
    _owns_client = False


def reset_database() -> None:
    """Drop the cached client so the next call opens a fresh database."""
    global _client, _db, _owns_client, _indexes_ready
    if _client is not None:
        close = getattr(_client, "close", None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
    _client = None
    _db = None
    _owns_client = False
    _indexes_ready = False


async def ensure_indexes(db) -> None:
    """Indexes the API and the judgment layer rely on. Safe to run again."""
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")
    await db.users.create_index("legacy_student_id", unique=True, sparse=True)

    await db.chats.create_index("user_id")
    await db.chats.create_index([("user_id", 1), ("updated_at", -1)])

    await db.personas.create_index("user_id", unique=True)

    await db.jds.create_index("user_id")
    await db.jds.create_index("content_hash")

    await db.tests.create_index("jd_id", unique=True)
    await db.tests.create_index("cache_key")
    await db.tests.create_index("user_id")

    await db.submissions.create_index([("user_id", 1), ("created_at", -1)])

    await db.kb_pending.create_index("status")
    await db.kb_pending.create_index("legacy_id", unique=True, sparse=True)
    await db.kb_pending.create_index([("status", 1), ("created_at", 1)])
    await db.kb_pending.create_index([("status", 1), ("updated_at", -1)])
    await db.kb_pending.create_index("created_at")
    await db.kb_pending.create_index("topic")
    await db.kb_pending.create_index("type")
    await db.kb_pending.create_index("source")
    await db.kb_pending.create_index("tags")

    await db.kb_uploads.create_index([("created_at", -1)])
    await db.kb_uploads.create_index("status")
    await db.kb_uploads.create_index("uploaded_by")
    await db.kb_uploads.create_index("kb_item_id")

    await db.activity.create_index([("user_id", 1), ("ts", -1)])
    await db.activity.create_index([("ts", -1)])
    await db.activity.create_index([("user_id", 1), ("type", 1), ("ts", -1)])

    # Teacher-authored timed tests. Separate from the JD ``tests`` collection.
    await db.class_tests.create_index("created_by", name="class_tests_created_by")
    await db.class_tests.create_index([("published", 1), ("updated_at", -1)], name="class_tests_published")
    await db.class_tests.create_index("topic", name="class_tests_topic")
    await db.class_tests.create_index("test_type", name="class_tests_type")

    await db.class_attempts.create_index([("test_id", 1), ("user_id", 1)], name="class_attempts_test_user")
    await db.class_attempts.create_index([("user_id", 1), ("started_at", -1)], name="class_attempts_user_started")
    await db.class_attempts.create_index([("test_id", 1), ("status", 1)], name="class_attempts_test_status")


async def get_db():
    """Return the application database, creating indexes on first use."""
    global _client, _db, _owns_client, _indexes_ready
    if _db is None:
        from rag_core.config import mongo_db_name, mongo_uri

        if os.getenv("CODELENS_MONGO_MOCK") == "1":
            from mongomock_motor import AsyncMongoMockClient

            _client = AsyncMongoMockClient()
            _db = _client[mongo_db_name()]
            _owns_client = False
        else:
            from motor.motor_asyncio import AsyncIOMotorClient

            _client = AsyncIOMotorClient(mongo_uri(), serverSelectionTimeoutMS=5000)
            _db = _client[mongo_db_name()]
            _owns_client = True
    if not _indexes_ready:
        await ensure_indexes(_db)
        _indexes_ready = True
    return _db


async def close_mongo() -> None:
    """Close a client this process opened. Injected test databases stay put."""
    global _client, _db, _owns_client, _indexes_ready
    if _owns_client and _client is not None:
        _client.close()
        _client = None
        _db = None
        _owns_client = False
        _indexes_ready = False


async def ping(*, quiet: bool = False) -> None:
    db = await get_db()
    await db.command("ping")
    if quiet:
        return
    from rag_core.config import mongo_db_name

    logger.info("mongodb ready db=%s", mongo_db_name())
