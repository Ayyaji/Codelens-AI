"""MongoDB reads and writes for the CodeLens collections.

The HTTP layer and the agents call these functions. Nothing here talks to
Chroma. Approved rows store ``chroma_ids`` for the vectors ``kb_update`` wrote;
this module only keeps that list. Upload chunks live in ``kb_uploads`` until a
teacher accepts them into ``kb_pending``.
"""

import copy
import re
import uuid
from datetime import datetime

from pymongo.errors import DuplicateKeyError

from rag_core.mongo import as_naive, as_object_id, get_db, iso, utcnow

NOTE_LIMIT = 100
SCORE_LIMIT = 200


def plain(value):
    """Make a Mongo value safe to put in a JSON response."""
    from bson import ObjectId

    if isinstance(value, datetime):
        return iso(value)
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def _message(role: str, content: str, directive: str | None, agent: str | None, when: datetime) -> dict:
    return {
        "role": role,
        "content": content,
        "directive": directive,
        "agent_used": agent,
        "ts": when,
    }


def message_out(message: dict) -> dict:
    return {
        "role": message.get("role") or "user",
        "content": message.get("content") or "",
        "directive": message.get("directive"),
        "agent_used": message.get("agent_used"),
        "ts": iso(message.get("ts")) or "",
    }


def chat_title(query: str) -> str:
    compact = " ".join(query.split()) or "Chat"
    if len(compact) <= 80:
        return compact
    return compact[:77].rstrip() + "..."


async def create_user(
    name: str,
    email: str,
    password_hash: str,
    role: str = "student",
    legacy_student_id: str | None = None,
) -> dict:
    db = await get_db()
    doc = {
        "name": name,
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "role": role,
        "disabled": False,
        "created_at": utcnow(),
    }
    if legacy_student_id:
        doc["legacy_student_id"] = legacy_student_id
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def find_user_by_email(email: str) -> dict | None:
    db = await get_db()
    return await db.users.find_one({"email": email.strip().lower()})


async def find_user(user_id: str) -> dict | None:
    oid = as_object_id(user_id)
    if oid is None:
        return None
    db = await get_db()
    return await db.users.find_one({"_id": oid})


async def find_user_by_legacy(student_id: str) -> dict | None:
    db = await get_db()
    return await db.users.find_one({"legacy_student_id": student_id})


async def set_disabled(user_id: str, disabled: bool) -> bool:
    oid = as_object_id(user_id)
    if oid is None:
        return False
    db = await get_db()
    result = await db.users.update_one(
        {"_id": oid, "role": "student"},
        {"$set": {"disabled": bool(disabled)}},
    )
    return result.matched_count == 1


async def save_turn(
    user_id: str,
    chat_id: str | None,
    query: str,
    answer: str,
    directive: str,
    agent: str,
) -> str:
    """Append one exchange, or open a chat when ``chat_id`` is missing."""
    db = await get_db()
    now = utcnow()
    messages = [
        _message("user", query, None, None, now),
        _message("assistant", answer, directive, agent, now),
    ]
    if chat_id:
        oid = as_object_id(chat_id)
        if oid is None:
            raise LookupError(chat_id)
        result = await db.chats.update_one(
            {"_id": oid, "user_id": user_id},
            {"$push": {"messages": {"$each": messages}}, "$set": {"updated_at": now}},
        )
        if result.matched_count == 0:
            raise LookupError(chat_id)
        return chat_id
    inserted = await db.chats.insert_one(
        {
            "user_id": user_id,
            "title": chat_title(query),
            "messages": messages,
            "created_at": now,
            "updated_at": now,
        }
    )
    return str(inserted.inserted_id)


async def get_chat(user_id: str, chat_id: str) -> dict | None:
    oid = as_object_id(chat_id)
    if oid is None:
        return None
    db = await get_db()
    return await db.chats.find_one({"_id": oid, "user_id": user_id})


async def list_chats(user_id: str) -> list[dict]:
    db = await get_db()
    cursor = db.chats.find({"user_id": user_id}, {"title": 1, "updated_at": 1}).sort("updated_at", -1)
    rows = await cursor.to_list(length=500)
    return [
        {
            "chat_id": str(row["_id"]),
            "title": row.get("title") or "Chat",
            "updated_at": iso(row.get("updated_at")) or "",
        }
        for row in rows
    ]


async def chat_detail(user_id: str, chat_id: str) -> dict | None:
    doc = await get_chat(user_id, chat_id)
    if doc is None:
        return None
    return {
        "chat_id": str(doc["_id"]),
        "title": doc.get("title") or "Chat",
        "messages": [message_out(message) for message in doc.get("messages") or []],
    }


def _score_out(entry: dict) -> dict:
    return {
        "test_id": str(entry.get("test_id") or ""),
        "score": float(entry.get("score") or 0),
        "created_at": iso(entry.get("created_at")) or "",
    }


async def hydrate_jds(jd_ids: list[str]) -> list[dict]:
    if not jd_ids:
        return []
    db = await get_db()
    docs = await db.jds.find({"_id": {"$in": list(jd_ids)}}).to_list(length=500)
    by_id = {doc["_id"]: doc for doc in docs}
    found = []
    for jd_id in jd_ids:
        doc = by_id.get(jd_id)
        if doc is None:
            continue
        found.append(
            {
                "jd_id": jd_id,
                "filename": doc.get("filename") or "jd.txt",
                "created_at": iso(doc.get("created_at")) or "",
            }
        )
    return found


async def persona_view(user_id: str) -> dict:
    db = await get_db()
    doc = await db.personas.find_one({"user_id": user_id})
    if doc is None:
        return {"weak_topics": [], "mistake_patterns": [], "scores": [], "jds": []}
    return {
        "weak_topics": list(doc.get("weak_topics") or []),
        "mistake_patterns": list(doc.get("mistake_patterns") or []),
        "scores": [_score_out(entry) for entry in doc.get("scores") or [] if isinstance(entry, dict)],
        "jds": await hydrate_jds(list(doc.get("jd_ids") or [])),
    }


async def teacher_persona(user_id: str) -> dict:
    view = await persona_view(user_id)
    db = await get_db()
    doc = await db.personas.find_one({"user_id": user_id})
    view["learning_notes"] = list((doc or {}).get("learning_notes") or [])
    view["updated_at"] = iso(doc.get("updated_at")) if doc else None
    return view


async def note_chat(user_id: str, query: str, directive: str, agent: str) -> None:
    """Record that a guidance turn happened. Called after every chat answer."""
    snippet = " ".join((query or "").split())
    if len(snippet) > 160:
        snippet = snippet[:157].rstrip() + "..."
    note = f"{directive} via {agent}: {snippet}" if snippet else f"{directive} via {agent}"
    db = await get_db()
    now = utcnow()
    await db.personas.update_one(
        {"user_id": user_id},
        {
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "weak_topics": [],
                "mistake_patterns": [],
                "scores": [],
                "jd_ids": [],
            },
            "$push": {"learning_notes": {"$each": [note], "$slice": -NOTE_LIMIT}},
        },
        upsert=True,
    )


async def remember_jd(user_id: str, jd_id: str) -> None:
    db = await get_db()
    now = utcnow()
    await db.personas.update_one(
        {"user_id": user_id},
        {
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "weak_topics": [],
                "mistake_patterns": [],
                "scores": [],
                "learning_notes": [],
            },
            "$addToSet": {"jd_ids": jd_id},
        },
        upsert=True,
    )


async def apply_attempt(
    user_id: str,
    jd_id: str,
    weak_topics: list[str],
    mistake_patterns: list[str],
    score: float,
    test_id: str,
) -> None:
    """Replace the current weaknesses and append the score. One persona per student."""
    topics = ", ".join(weak_topics) if weak_topics else "none"
    note = f"score {round(float(score), 1)} weak {topics}"
    now = utcnow()
    db = await get_db()
    await db.personas.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "updated_at": now,
                "weak_topics": list(weak_topics),
                "mistake_patterns": list(mistake_patterns),
            },
            "$addToSet": {"jd_ids": jd_id},
            "$push": {
                "scores": {
                    "$each": [
                        {
                            "test_id": test_id,
                            "score": float(score),
                            "created_at": now,
                        }
                    ],
                    "$slice": -SCORE_LIMIT,
                },
                "learning_notes": {"$each": [note], "$slice": -NOTE_LIMIT},
            },
        },
        upsert=True,
    )


async def insert_jd(user_id: str, text: str, filename: str, digest: str) -> str:
    db = await get_db()
    jd_id = uuid.uuid4().hex
    await db.jds.insert_one(
        {
            "_id": jd_id,
            "user_id": user_id,
            "content_hash": digest,
            "filename": (filename or "jd.txt")[:200],
            "raw_text": text,
            "analysis": None,
            "created_at": utcnow(),
        }
    )
    await remember_jd(user_id, jd_id)
    return jd_id


async def get_jd(jd_id: str, user_id: str) -> dict | None:
    db = await get_db()
    return await db.jds.find_one({"_id": jd_id, "user_id": user_id})


async def find_analysis(digest: str) -> dict | None:
    db = await get_db()
    doc = await db.jds.find_one({"content_hash": digest, "analysis": {"$ne": None}}, {"analysis": 1})
    if not doc:
        return None
    analysis = doc.get("analysis")
    return analysis if isinstance(analysis, dict) else None


async def save_analysis(jd_id: str, analysis: dict) -> None:
    db = await get_db()
    await db.jds.update_one({"_id": jd_id}, {"$set": {"analysis": analysis}})


async def list_user_jds(user_id: str) -> list[dict]:
    db = await get_db()
    cursor = db.jds.find({"user_id": user_id}, {"filename": 1, "created_at": 1}).sort("created_at", -1)
    rows = await cursor.to_list(length=500)
    return [
        {
            "jd_id": row["_id"],
            "filename": row.get("filename") or "jd.txt",
            "created_at": iso(row.get("created_at")) or "",
        }
        for row in rows
    ]


async def questions_for_jd(jd_id: str) -> list[dict] | None:
    db = await get_db()
    doc = await db.tests.find_one({"jd_id": jd_id}, {"questions": 1})
    if doc is None:
        return None
    return copy.deepcopy(doc.get("questions") or [])


async def questions_for_cache(cache_key: str) -> list[dict] | None:
    db = await get_db()
    doc = await db.tests.find_one({"cache_key": cache_key}, {"questions": 1})
    if doc is None:
        return None
    return copy.deepcopy(doc.get("questions") or [])


async def save_test(jd_id: str, user_id: str, cache_key: str, questions: list[dict]) -> None:
    db = await get_db()
    await db.tests.update_one(
        {"jd_id": jd_id},
        {
            "$set": {
                "user_id": user_id,
                "cache_key": cache_key,
                "questions": copy.deepcopy(questions),
            },
            "$setOnInsert": {"created_at": utcnow()},
        },
        upsert=True,
    )


async def insert_submission(
    user_id: str,
    jd_id: str,
    score: float,
    answers: list,
    weak_topics: list[str],
    mistake_patterns: list[str],
) -> str:
    from bson import ObjectId

    db = await get_db()
    oid = ObjectId()
    now = utcnow()
    await db.submissions.insert_one(
        {
            "_id": oid,
            "user_id": user_id,
            "jd_id": jd_id,
            "score": float(score),
            "answers": answers,
            "weak_topics": list(weak_topics),
            "mistake_patterns": list(mistake_patterns),
            "created_at": now,
        }
    )
    return str(oid)


async def list_attempts(user_id: str) -> list[dict]:
    db = await get_db()
    cursor = db.submissions.find({"user_id": user_id}, {"score": 1, "created_at": 1}).sort("created_at", -1)
    rows = await cursor.to_list(length=500)
    return [
        {
            "test_id": str(row["_id"]),
            "score": float(row.get("score") or 0),
            "created_at": iso(row.get("created_at")) or "",
        }
        for row in rows
    ]


async def history_view(user_id: str) -> dict:
    return {"jds": await list_user_jds(user_id), "tests": await list_attempts(user_id)}


async def add_activity(user_id: str, activity_type: str, detail: dict | None = None, ts: datetime | None = None) -> str:
    db = await get_db()
    result = await db.activity.insert_one(
        {
            "user_id": user_id,
            "type": activity_type,
            "detail": detail or {},
            "ts": as_naive(ts) if ts is not None else utcnow(),
        }
    )
    return str(result.inserted_id)


async def judgment_history(user_id: str, cutoff: datetime) -> list[dict]:
    """Ask and test-submit events newer than ``cutoff``, newest first.

    This is the history the judgment layer used to read from the SQLite
    ``sessions`` table.
    """
    db = await get_db()
    cursor = (
        db.activity.find(
            {
                "user_id": user_id,
                "type": {"$in": ["ask", "test_submit"]},
                "ts": {"$gt": as_naive(cutoff)},
            }
        )
        .sort("ts", -1)
    )
    return await cursor.to_list(length=500)


def _activity_out(doc: dict, users_by_id: dict | None = None) -> dict:
    user_id = doc.get("user_id")
    item = {
        "id": str(doc["_id"]),
        "user_id": user_id,
        "type": doc.get("type") or "",
        "detail": plain(doc.get("detail") or {}),
        "ts": iso(doc.get("ts")) or "",
    }
    if users_by_id is not None:
        user = users_by_id.get(user_id) or {}
        item["name"] = user.get("name")
        item["email"] = user.get("email")
    return item


async def recent_activity(user_id: str, limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = db.activity.find({"user_id": user_id}).sort("ts", -1).limit(limit)
    rows = await cursor.to_list(length=limit)
    return [_activity_out(row) for row in rows]


async def _student_docs() -> list[dict]:
    db = await get_db()
    return await db.users.find({"role": "student"}).to_list(length=10000)


def _mean(scores: list[float]) -> float | None:
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


async def _score_buckets() -> dict[str, list[float]]:
    db = await get_db()
    buckets: dict[str, list[float]] = {}
    async for doc in db.submissions.find({}, {"user_id": 1, "score": 1}):
        buckets.setdefault(doc.get("user_id"), []).append(float(doc.get("score") or 0))
    return buckets


async def student_rows() -> list[dict]:
    db = await get_db()
    students = await _student_docs()
    ids = {str(doc["_id"]) for doc in students}
    last: dict[str, datetime] = {}
    async for doc in db.activity.find({}, {"user_id": 1, "ts": 1}):
        user_id = doc.get("user_id")
        ts = as_naive(doc.get("ts"))
        if user_id not in ids or not isinstance(ts, datetime):
            continue
        if user_id not in last or ts > last[user_id]:
            last[user_id] = ts
    weak = {}
    async for doc in db.personas.find({}, {"user_id": 1, "weak_topics": 1}):
        weak[doc.get("user_id")] = list(doc.get("weak_topics") or [])
    buckets = await _score_buckets()
    rows = []
    for doc in students:
        user_id = str(doc["_id"])
        rows.append(
            {
                "id": user_id,
                "name": doc.get("name") or "",
                "email": doc.get("email") or "",
                "disabled": bool(doc.get("disabled")),
                "last_active": iso(last.get(user_id)),
                "avg_score": _mean(buckets.get(user_id, [])),
                "weak_topics": weak.get(user_id, []),
            }
        )
    rows.sort(key=lambda row: (row["name"].casefold(), row["email"]))
    return rows


async def student_row(user_id: str) -> dict | None:
    for row in await student_rows():
        if row["id"] == user_id:
            return row
    return None


async def student_detail(user_id: str) -> dict | None:
    user = await find_user(user_id)
    if user is None or user.get("role") != "student":
        return None
    return {
        "user": {
            "id": str(user["_id"]),
            "name": user.get("name") or "",
            "email": user.get("email") or "",
            "role": user.get("role"),
            "disabled": bool(user.get("disabled")),
            "created_at": iso(user.get("created_at")),
        },
        "persona": await teacher_persona(user_id),
        "recent_activity": await recent_activity(user_id, 20),
        "tests": await list_attempts(user_id),
    }


async def teacher_overview() -> dict:
    db = await get_db()
    students = await _student_docs()
    ids = {str(doc["_id"]) for doc in students}
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active: set[str] = set()
    directives = {"full": 0, "hint": 0, "gentle": 0, "break": 0}
    async for doc in db.activity.find({}, {"user_id": 1, "ts": 1, "detail": 1}):
        user_id = doc.get("user_id")
        ts = as_naive(doc.get("ts"))
        if user_id in ids and isinstance(ts, datetime) and ts >= start:
            active.add(user_id)
        directive = (doc.get("detail") or {}).get("directive")
        if directive in directives:
            directives[directive] += 1
    total_score = 0.0
    total_count = 0
    async for doc in db.submissions.find({}, {"score": 1}):
        total_score += float(doc.get("score") or 0)
        total_count += 1
    pending = await db.kb_pending.count_documents({"status": "pending"})
    return {
        "total_students": len(students),
        "active_today": len(active),
        "avg_score": round(total_score / total_count, 1) if total_count else 0.0,
        "directive_counts": directives,
        "pending_kb": pending,
    }


async def activity_feed(limit: int) -> list[dict]:
    db = await get_db()
    students = await _student_docs()
    ids = [str(doc["_id"]) for doc in students]
    by_id = {str(doc["_id"]): doc for doc in students}
    cursor = db.activity.find({"user_id": {"$in": ids}}).sort("ts", -1).limit(limit)
    rows = await cursor.to_list(length=limit)
    return [_activity_out(row, by_id) for row in rows]


async def wipe_student(user_id: str) -> None:
    """Clear learning data. The account itself stays, including the disabled flag."""
    db = await get_db()
    await db.chats.delete_many({"user_id": user_id})
    await db.personas.delete_many({"user_id": user_id})
    await db.submissions.delete_many({"user_id": user_id})
    await db.activity.delete_many({"user_id": user_id})
    await db.jds.delete_many({"user_id": user_id})
    await db.tests.delete_many({"user_id": user_id})


async def insert_kb(
    content: str,
    source: str | None,
    proposed_by: str | None,
    query: str | None = None,
    status: str = "pending",
    legacy_id: int | None = None,
    reviewed_by: str | None = None,
    reviewed_at: datetime | None = None,
    created_at: datetime | None = None,
    *,
    title: str | None = None,
    topic: str | None = None,
    tags: list | None = None,
    difficulty: str | None = None,
    note_type: str | None = None,
    origin: str | None = None,
    proposer_name: str | None = None,
    proposer_role: str | None = None,
    reject_reason: str | None = None,
    chroma_ids: list | None = None,
) -> str:
    db = await get_db()
    now = created_at or utcnow()
    doc = {
        "content": content,
        "source": source,
        "proposed_by": proposed_by,
        "query": query,
        "status": status,
        "reviewed_by": reviewed_by,
        "reviewed_at": reviewed_at,
        "created_at": now,
        "updated_at": now,
        "title": title,
        "topic": topic or "",
        "tags": list(tags or []),
        "difficulty": difficulty,
        "type": note_type or "concept",
        "origin": origin,
        "proposer_name": proposer_name,
        "proposer_role": proposer_role,
        "reject_reason": reject_reason,
        "chroma_ids": list(chroma_ids or []),
    }
    if legacy_id is not None:
        doc["legacy_id"] = legacy_id
    try:
        result = await db.kb_pending.insert_one(doc)
    except DuplicateKeyError:
        existing = await db.kb_pending.find_one({"legacy_id": legacy_id})
        return str(existing["_id"]) if existing else ""
    return str(result.inserted_id)


async def find_kb(item_id: str) -> dict | None:
    oid = as_object_id(item_id)
    if oid is None:
        return None
    db = await get_db()
    return await db.kb_pending.find_one({"_id": oid})


async def users_by_ids(ids: list) -> dict:
    oids = []
    for value in ids:
        oid = as_object_id(value) if value else None
        if oid is not None:
            oids.append(oid)
    if not oids:
        return {}
    db = await get_db()
    found = await db.users.find({"_id": {"$in": oids}}, {"name": 1, "role": 1}).to_list(length=len(oids))
    return {str(doc["_id"]): {"name": doc.get("name"), "role": doc.get("role")} for doc in found}


def kb_public(doc: dict, users: dict | None = None) -> dict:
    proposed_by = doc.get("proposed_by")
    user = (users or {}).get(str(proposed_by)) if proposed_by else None
    tags = doc.get("tags") if isinstance(doc.get("tags"), list) else []
    title = doc.get("title") or doc.get("query") or "Untitled"
    return {
        "id": str(doc["_id"]),
        "title": title,
        "content": doc.get("content") or "",
        "topic": doc.get("topic") or "",
        "tags": [str(tag) for tag in tags if str(tag).strip()],
        "difficulty": doc.get("difficulty") or None,
        "source": doc.get("source"),
        "type": doc.get("type") or "concept",
        "origin": doc.get("origin") or None,
        "proposed_by": proposed_by,
        "proposer_name": doc.get("proposer_name") or (user or {}).get("name"),
        "proposer_role": doc.get("proposer_role") or (user or {}).get("role"),
        "status": doc.get("status") or "pending",
        "query": doc.get("query") or doc.get("title"),
        "reviewed_by": doc.get("reviewed_by"),
        "reviewed_at": iso(doc.get("reviewed_at")),
        "reject_reason": doc.get("reject_reason") or None,
        "created_at": iso(doc.get("created_at")),
        "updated_at": iso(doc.get("updated_at") or doc.get("created_at")),
    }


async def kb_public_many(docs: list[dict]) -> list[dict]:
    users = await users_by_ids([doc.get("proposed_by") for doc in docs])
    return [kb_public(doc, users) for doc in docs]


async def kb_public_one(doc: dict) -> dict:
    rows = await kb_public_many([doc])
    return rows[0]


async def list_pending_kb() -> list[dict]:
    db = await get_db()
    cursor = db.kb_pending.find({"status": "pending"}).sort("created_at", 1)
    rows = await cursor.to_list(length=500)
    return await kb_public_many(rows)


async def update_kb_fields(item_id: str, fields: dict, *, chroma_ids: list | None = None) -> dict:
    doc = await find_kb(item_id)
    if doc is None:
        raise LookupError(item_id)
    if doc.get("status") not in {"pending", "approved"}:
        raise ValueError("Only a pending or approved item can be edited")
    updates = dict(fields)
    updates["updated_at"] = utcnow()
    if chroma_ids is not None:
        updates["chroma_ids"] = list(chroma_ids)
    db = await get_db()
    await db.kb_pending.update_one({"_id": doc["_id"]}, {"$set": updates})
    doc.update(updates)
    return doc


async def set_kb_status(
    item_id: str,
    status: str,
    reviewer_id: str,
    *,
    reject_reason: str | None = None,
    chroma_ids: list | None = None,
) -> dict:
    doc = await find_kb(item_id)
    if doc is None:
        raise LookupError(item_id)
    if doc.get("status") != "pending":
        raise ValueError(f"Only a pending item can be {status}")
    db = await get_db()
    reviewed_at = utcnow()
    updates = {
        "status": status,
        "reviewed_by": reviewer_id,
        "reviewed_at": reviewed_at,
        "updated_at": reviewed_at,
        "reject_reason": reject_reason if status == "rejected" else None,
    }
    if chroma_ids is not None:
        updates["chroma_ids"] = list(chroma_ids)
    await db.kb_pending.update_one({"_id": doc["_id"]}, {"$set": updates})
    doc.update(updates)
    return doc


async def remove_kb(item_id: str) -> dict | None:
    doc = await find_kb(item_id)
    if doc is None:
        return None
    db = await get_db()
    await db.kb_pending.delete_one({"_id": doc["_id"]})
    return doc


def _kb_query(*, q: str, topic: str, tag: str, note_type: str, source: str, start, end) -> dict:
    query: dict = {}
    if topic:
        query["topic"] = topic
    if tag:
        query["tags"] = tag
    if note_type:
        query["type"] = note_type
    if source:
        query["source"] = source
    created = {}
    if start is not None:
        created["$gte"] = start
    if end is not None:
        created["$lte"] = end
    if created:
        query["created_at"] = created
    if q:
        pattern = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [
            {"title": pattern},
            {"content": pattern},
            {"topic": pattern},
            {"query": pattern},
            {"tags": pattern},
        ]
    return query


async def search_kb_rows(*, q: str, topic: str, tag: str, note_type: str, source: str, start, end) -> list[dict]:
    """Notes matching every filter except status. The caller counts and pages."""
    db = await get_db()
    query = _kb_query(q=q, topic=topic, tag=tag, note_type=note_type, source=source, start=start, end=end)
    return await db.kb_pending.find(query).to_list(length=10_000)


async def kb_facets() -> dict:
    db = await get_db()
    rows = await db.kb_pending.find({}, {"topic": 1, "tags": 1, "type": 1, "source": 1}).to_list(length=10_000)
    topics: list[str] = []
    tags: list[str] = []
    types: list[str] = []
    sources: list[str] = []

    def push(bucket: list[str], value) -> None:
        text = str(value or "").strip()
        if text and text not in bucket:
            bucket.append(text)

    for row in rows:
        push(topics, row.get("topic"))
        push(types, row.get("type"))
        push(sources, row.get("source"))
        for tag in row.get("tags") or []:
            push(tags, tag)
    topics.sort(key=str.lower)
    tags.sort(key=str.lower)
    types.sort(key=str.lower)
    sources.sort(key=str.lower)
    return {"topics": topics, "tags": tags, "types": types, "sources": sources}


async def insert_upload(doc: dict) -> str:
    db = await get_db()
    result = await db.kb_uploads.insert_one(doc)
    return str(result.inserted_id)


async def find_upload(upload_id: str) -> dict | None:
    oid = as_object_id(upload_id)
    if oid is None:
        return None
    db = await get_db()
    return await db.kb_uploads.find_one({"_id": oid})


async def list_uploads() -> list[dict]:
    db = await get_db()
    cursor = db.kb_uploads.find().sort("created_at", -1)
    return await cursor.to_list(length=500)


async def attach_upload(upload_id: str, item_id: str) -> None:
    oid = as_object_id(upload_id)
    if oid is None:
        return
    db = await get_db()
    await db.kb_uploads.update_one({"_id": oid}, {"$set": {"kb_item_id": item_id, "status": "chunked", "progress": 100}})


async def delete_upload(upload_id: str) -> bool:
    oid = as_object_id(upload_id)
    if oid is None:
        return False
    db = await get_db()
    result = await db.kb_uploads.delete_one({"_id": oid})
    return result.deleted_count == 1


def upload_public(doc: dict) -> dict:
    chunks = doc.get("chunks") if isinstance(doc.get("chunks"), list) else []
    return {
        "id": str(doc["_id"]),
        "filename": doc.get("filename") or "",
        "media_type": doc.get("media_type") or "",
        "size": int(doc.get("size") or 0),
        "status": doc.get("status") or "processing",
        "progress": int(doc.get("progress") or 0),
        "error": doc.get("error") or "",
        "created_at": iso(doc.get("created_at")),
        "kb_item_id": doc.get("kb_item_id") or None,
        "chunks": [
            {
                "index": int(chunk.get("index", index)),
                "title": str(chunk.get("title") or f"Chunk {index + 1}"),
                "content": str(chunk.get("content") or ""),
            }
            for index, chunk in enumerate(chunks)
            if isinstance(chunk, dict)
        ],
    }
