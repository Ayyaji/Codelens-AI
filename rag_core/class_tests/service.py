"""Create, publish, sit, and grade teacher-authored tests.

Documents live in ``class_tests`` and ``class_attempts``. The JD collections
``tests`` and ``submissions`` are not written here.
"""

import copy
import csv
import io
import uuid
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo import ReturnDocument

from rag_core.agents.diagnoser import summarise_attempt
from rag_core.class_tests.bank import bank_questions, bank_totals
from rag_core.class_tests.errors import ClassTestError
from rag_core.class_tests.grading import grade_questions, public_question, public_result, run_visible
from rag_core.class_tests.shuffle import build_layout, present_questions
from rag_core.mongo import as_naive, as_object_id, get_db, iso, utcnow
from rag_core.store import add_activity, apply_attempt

_TEST_TYPES = {"mcq": {"mcq"}, "coding": {"coding"}, "mixed": {"mcq", "short", "coding"}}
_FINAL = {"submitted", "expired"}
_MAX_CODE = 20_000
_MAX_TEXT = 4_000


def _aware_to_naive(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return as_naive(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ClassTestError(422, "Dates must be ISO-8601 timestamps") from exc
    return as_naive(parsed)


def _in_window(doc: dict, now: datetime) -> bool:
    start = as_naive(doc.get("available_from"))
    end = as_naive(doc.get("available_until"))
    if isinstance(start, datetime) and now < start:
        return False
    if isinstance(end, datetime) and now > end:
        return False
    return True


def _cases(raw, label: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ClassTestError(422, f"{label} must be a list")
    if len(raw) > 20:
        raise ClassTestError(422, f"{label} can have at most 20 cases")
    cases = []
    for index, case in enumerate(raw, start=1):
        if not isinstance(case, dict):
            raise ClassTestError(422, f"{label} case {index} must be an object")
        stdin = case.get("stdin", case.get("input", ""))
        expected = case.get("expected", "")
        cases.append({"stdin": "" if stdin is None else str(stdin), "expected": "" if expected is None else str(expected).strip()})
    return cases


def _keywords(raw) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        parts = raw.split(",")
    elif isinstance(raw, list):
        parts = raw
    else:
        raise ClassTestError(422, "keywords must be a list or a comma-separated string")
    words = []
    for part in parts:
        text = str(part).strip()
        if text:
            words.append(text[:80])
    return words[:12]


def normalize_question(raw: dict, index: int, allowed: set[str]) -> dict:
    if not isinstance(raw, dict):
        raise ClassTestError(422, f"Question {index} must be an object")
    kind = str(raw.get("type") or "").strip().lower()
    if kind not in allowed:
        if kind == "mcq" and "mcq" not in allowed:
            raise ClassTestError(422, "A coding test can only contain coding questions")
        if kind == "coding" and "coding" not in allowed:
            raise ClassTestError(422, "An MCQ test can only contain multiple-choice questions")
        if kind == "short":
            raise ClassTestError(422, "Short-answer questions belong on a mixed test")
        raise ClassTestError(422, f"Question {index} has an unknown type")
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        raise ClassTestError(422, f"Question {index} needs a prompt")
    if len(prompt) > 4000:
        raise ClassTestError(422, f"Question {index} prompt is too long")
    skill = str(raw.get("skill") or raw.get("topic") or "general").strip() or "general"
    qid = str(raw.get("id") or "").strip() or f"q_{uuid.uuid4().hex[:10]}"
    explanation = str(raw.get("explanation") or "").strip()[:2000]
    base = {"id": qid[:40], "type": kind, "skill": skill[:60], "prompt": prompt, "explanation": explanation}
    if kind == "mcq":
        options_raw = raw.get("options")
        if not isinstance(options_raw, list) or not 2 <= len(options_raw) <= 6:
            raise ClassTestError(422, f"Question {index} needs 2 to 6 options")
        options = []
        for option in options_raw:
            text = str(option).strip()
            if not text:
                raise ClassTestError(422, f"Question {index} has a blank option")
            options.append(text[:300])
        try:
            correct_index = int(raw.get("correct_index"))
        except (TypeError, ValueError) as exc:
            raise ClassTestError(422, f"Question {index} needs a correct_index") from exc
        if not 0 <= correct_index < len(options):
            raise ClassTestError(422, f"Question {index} correct_index is outside the options")
        base["options"] = options
        base["correct_index"] = correct_index
        return base
    if kind == "short":
        expected = str(raw.get("expected") or "").strip()
        keywords = _keywords(raw.get("keywords"))
        if not expected and not keywords:
            raise ClassTestError(422, f"Question {index} needs an expected answer or keywords")
        base["expected"] = expected[:500]
        base["keywords"] = keywords or ([expected[:80]] if expected else [])
        return base
    signature = str(raw.get("signature") or "def solve():").strip()[:200]
    starter = raw.get("starter_code")
    starter = "" if starter is None else str(starter)
    if len(starter) > _MAX_CODE:
        raise ClassTestError(422, f"Question {index} starter code is too long")
    language = str(raw.get("language") or "python").strip().lower()
    if language not in {"python", "py", "python3"}:
        raise ClassTestError(422, f"Question {index} must use Python")
    visible = _cases(raw.get("visible_cases"), f"Question {index} visible cases")
    hidden = _cases(raw.get("hidden_cases"), f"Question {index} hidden cases")
    if not visible and not hidden:
        raise ClassTestError(422, f"Question {index} needs at least one test case")
    base["signature"] = signature
    base["starter_code"] = starter
    base["language"] = "python"
    base["visible_cases"] = visible
    base["hidden_cases"] = hidden
    return base


def normalize_questions(raw, test_type: str) -> list[dict]:
    allowed = _TEST_TYPES[test_type]
    if not isinstance(raw, list) or not raw:
        raise ClassTestError(422, "Add at least one question")
    if len(raw) > 40:
        raise ClassTestError(422, "A test can have at most 40 questions")
    questions = []
    seen = set()
    for index, item in enumerate(raw, start=1):
        question = normalize_question(item, index, allowed)
        qid = question["id"]
        if qid in seen:
            qid = f"{qid[:28]}_{index}"
            question["id"] = qid
        seen.add(qid)
        questions.append(question)
    return questions


def _test_fields(body: dict, *, require_questions: bool) -> dict:
    title = str(body.get("title") or "").strip()
    if not title:
        raise ClassTestError(422, "A test needs a title")
    if len(title) > 140:
        raise ClassTestError(422, "The title is longer than 140 characters")
    description = str(body.get("description") or "").strip()
    if len(description) > 4000:
        raise ClassTestError(422, "The description is longer than 4000 characters")
    test_type = str(body.get("test_type") or "").strip().lower()
    if test_type not in _TEST_TYPES:
        raise ClassTestError(422, "test_type must be mcq, coding, or mixed")
    topic = str(body.get("topic") or "general").strip() or "general"
    if len(topic) > 60:
        raise ClassTestError(422, "The topic is longer than 60 characters")
    try:
        duration = int(body.get("duration_minutes"))
    except (TypeError, ValueError) as exc:
        raise ClassTestError(422, "duration_minutes must be a whole number") from exc
    if not 1 <= duration <= 240:
        raise ClassTestError(422, "duration_minutes must be between 1 and 240")
    start = _aware_to_naive(body.get("available_from"))
    end = _aware_to_naive(body.get("available_until"))
    if start and end and end < start:
        raise ClassTestError(422, "available_until is earlier than available_from")
    fields = {
        "title": title,
        "description": description,
        "topic": topic,
        "test_type": test_type,
        "duration_minutes": duration,
        "available_from": start,
        "available_until": end,
        "published": bool(body.get("published")),
        "allow_retake": bool(body.get("allow_retake")),
        "show_answers_after_submit": bool(body.get("show_answers_after_submit")),
        "shuffle_questions": bool(body.get("shuffle_questions")),
        "shuffle_options": bool(body.get("shuffle_options")),
    }
    if require_questions or "questions" in body:
        fields["questions"] = normalize_questions(body.get("questions"), test_type)
    return fields


def _summary(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title") or "",
        "description": doc.get("description") or "",
        "topic": doc.get("topic") or "general",
        "test_type": doc.get("test_type") or "mixed",
        "duration_minutes": int(doc.get("duration_minutes") or 0),
        "available_from": iso(doc.get("available_from")),
        "available_until": iso(doc.get("available_until")),
        "published": bool(doc.get("published")),
        "allow_retake": bool(doc.get("allow_retake")),
        "show_answers_after_submit": bool(doc.get("show_answers_after_submit")),
        "shuffle_questions": bool(doc.get("shuffle_questions")),
        "shuffle_options": bool(doc.get("shuffle_options")),
        "question_count": len(doc.get("questions") or []),
        "created_by": doc.get("created_by") or "",
        "created_at": iso(doc.get("created_at")),
        "updated_at": iso(doc.get("updated_at")),
    }


def _teacher_test(doc: dict) -> dict:
    payload = _summary(doc)
    payload["questions"] = copy.deepcopy(doc.get("questions") or [])
    payload["attempt_count"] = int(doc.get("attempt_count") or 0)
    return payload


def _phase(doc: dict, attempt: dict | None, now: datetime) -> str:
    """upcoming, active, completed, or closed. Used by the student list."""
    start = as_naive(doc.get("available_from"))
    finished = bool(attempt and attempt.get("status") in _FINAL)
    in_progress = bool(attempt and attempt.get("status") == "in_progress")
    if isinstance(start, datetime) and now < start and not in_progress:
        return "upcoming"
    if in_progress or (
        bool(doc.get("published"))
        and _in_window(doc, now)
        and (not finished or bool(doc.get("allow_retake")))
    ):
        return "active"
    if finished:
        return "completed"
    return "closed"


def _attempt_summary(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "status": doc.get("status"),
        "score": doc.get("score"),
        "started_at": iso(doc.get("started_at")),
        "deadline": iso(doc.get("deadline")),
        "submitted_at": iso(doc.get("submitted_at")),
        "time_taken_seconds": doc.get("time_taken_seconds"),
    }


async def _load_test(test_id: str) -> dict:
    oid = as_object_id(test_id)
    if oid is None:
        raise ClassTestError(404, "Test not found")
    db = await get_db()
    doc = await db.class_tests.find_one({"_id": oid})
    if doc is None:
        raise ClassTestError(404, "Test not found")
    return doc


async def _attempts_for(test_id: str, user_id: str) -> list[dict]:
    db = await get_db()
    cursor = db.class_attempts.find({"test_id": test_id, "user_id": user_id}).sort("started_at", -1)
    return await cursor.to_list(length=50)


def _pick_attempt(rows: list[dict]) -> dict | None:
    for row in rows:
        if row.get("status") == "in_progress":
            return row
    return rows[0] if rows else None


def _bank_visible(question: dict) -> dict:
    shown = {key: value for key, value in question.items() if key not in {"_id", "created_by"}}
    if "created_at" in shown:
        shown["created_at"] = iso(shown.get("created_at"))
    return shown


def _bank_match(question: dict, kind: str, topic_needle: str) -> bool:
    if kind and kind != "all" and question.get("type") != kind:
        return False
    if topic_needle:
        hay = f"{question.get('topic', '')} {question.get('skill', '')} {question.get('prompt', '')}".lower()
        if topic_needle not in hay:
            return False
    return True


async def list_bank(kind: str = "", topic: str = "") -> dict:
    kind = (kind or "").strip().lower()
    topic_needle = (topic or "").strip().lower()
    if kind in {"dsa", "code"}:
        kind = "coding"
    questions = []
    for question in bank_questions():
        if _bank_match(question, kind, topic_needle):
            questions.append(question)
    db = await get_db()
    saved = await db.class_question_bank.find({}).sort("created_at", -1).to_list(length=200)
    totals = bank_totals()
    for question in saved:
        qtype = question.get("type")
        if qtype in totals:
            totals[qtype] += 1
        elif qtype:
            totals[qtype] = totals.get(qtype, 0) + 1
        if _bank_match(question, kind, topic_needle):
            questions.append(_bank_visible(question))
    return {"questions": questions, "totals": totals}


async def save_bank_questions(teacher_id: str, raw_questions) -> dict:
    """Store teacher-reviewed questions. The seeded bank is left as it is."""
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ClassTestError(422, "Add at least one question")
    if len(raw_questions) > 40:
        raise ClassTestError(422, "Save at most 40 questions at once")
    now = utcnow()
    saved = []
    for index, raw in enumerate(raw_questions, start=1):
        if not isinstance(raw, dict):
            raise ClassTestError(422, f"Question {index} must be an object")
        kind = str(raw.get("type") or "").strip().lower()
        if kind not in {"mcq", "coding", "short"}:
            raise ClassTestError(422, f"Question {index} has an unknown type")
        question = normalize_question(raw, index, {kind})
        question["topic"] = str(raw.get("topic") or raw.get("skill") or "general").strip()[:60] or "general"
        question["source"] = "generated"
        question["created_by"] = teacher_id
        question["created_at"] = now
        saved.append(question)
    db = await get_db()
    await db.class_question_bank.insert_many(saved)
    return {"saved": len(saved), "questions": [_bank_visible(question) for question in saved]}


async def duplicate_test(test_id: str, teacher_id: str) -> dict:
    """A new unpublished copy. Question ids are new so the papers stay independent."""
    current = await _load_test(test_id)
    now = utcnow()
    suffix = " (copy)"
    base = str(current.get("title") or "Test").strip() or "Test"
    title = (base[: 140 - len(suffix)] + suffix).strip()
    questions = copy.deepcopy(current.get("questions") or [])
    for question in questions:
        question["id"] = f"q_{uuid.uuid4().hex[:10]}"
    doc = {
        "title": title,
        "description": current.get("description") or "",
        "topic": current.get("topic") or "general",
        "test_type": current.get("test_type") or "mixed",
        "duration_minutes": int(current.get("duration_minutes") or 20),
        "available_from": current.get("available_from"),
        "available_until": current.get("available_until"),
        "published": False,
        "allow_retake": bool(current.get("allow_retake")),
        "show_answers_after_submit": bool(current.get("show_answers_after_submit")),
        "shuffle_questions": bool(current.get("shuffle_questions")),
        "shuffle_options": bool(current.get("shuffle_options")),
        "questions": questions,
        "created_by": teacher_id,
        "updated_by": teacher_id,
        "created_at": now,
        "updated_at": now,
        "attempt_count": 0,
    }
    db = await get_db()
    result = await db.class_tests.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _teacher_test(doc)


async def create_test(teacher_id: str, body: dict) -> dict:
    fields = _test_fields(body, require_questions=True)
    now = utcnow()
    db = await get_db()
    doc = {**fields, "created_by": teacher_id, "updated_by": teacher_id, "created_at": now, "updated_at": now}
    result = await db.class_tests.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _teacher_test(doc)


async def update_test(test_id: str, teacher_id: str, body: dict) -> dict:
    current = await _load_test(test_id)
    db = await get_db()
    attempt_count = await db.class_attempts.count_documents({"test_id": str(current["_id"])})
    merged = {
        "title": body.get("title", current.get("title")),
        "description": body.get("description", current.get("description")),
        "topic": body.get("topic", current.get("topic")),
        "test_type": body.get("test_type", current.get("test_type")),
        "duration_minutes": body.get("duration_minutes", current.get("duration_minutes")),
        "available_from": body["available_from"] if "available_from" in body else current.get("available_from"),
        "available_until": body["available_until"] if "available_until" in body else current.get("available_until"),
        "published": body.get("published", current.get("published")),
        "allow_retake": body.get("allow_retake", current.get("allow_retake")),
        "show_answers_after_submit": body.get("show_answers_after_submit", current.get("show_answers_after_submit")),
        "shuffle_questions": body.get("shuffle_questions", current.get("shuffle_questions")),
        "shuffle_options": body.get("shuffle_options", current.get("shuffle_options")),
    }
    if "questions" in body:
        merged["questions"] = body.get("questions")
    fields = _test_fields(merged, require_questions="questions" in body)
    if "questions" not in fields:
        fields["questions"] = current.get("questions") or []
        # Re-check the type against the questions we are keeping.
        normalize_questions(fields["questions"], fields["test_type"])
    if attempt_count and "questions" in body:
        if fields["questions"] != (current.get("questions") or []):
            raise ClassTestError(409, "This test already has attempts, so its questions stay as they are")
    if attempt_count and fields["test_type"] != current.get("test_type"):
        raise ClassTestError(409, "This test already has attempts, so its type stays as it is")
    fields["updated_at"] = utcnow()
    fields["updated_by"] = teacher_id
    await db.class_tests.update_one({"_id": current["_id"]}, {"$set": fields})
    saved = await _load_test(str(current["_id"]))
    return _teacher_test(saved)


async def delete_test(test_id: str) -> dict:
    doc = await _load_test(test_id)
    db = await get_db()
    if await db.class_attempts.count_documents({"test_id": str(doc["_id"])}):
        raise ClassTestError(409, "This test has attempts. Unpublish it instead of deleting it")
    await db.class_tests.delete_one({"_id": doc["_id"]})
    return {"id": str(doc["_id"]), "deleted": True}


async def _attempt_counts(test_ids: list[str]) -> dict[str, int]:
    if not test_ids:
        return {}
    db = await get_db()
    counts: dict[str, int] = {}
    cursor = db.class_attempts.find({"test_id": {"$in": test_ids}}, {"test_id": 1})
    for row in await cursor.to_list(length=2000):
        key = row.get("test_id")
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


async def list_tests_for_teacher() -> dict:
    db = await get_db()
    cursor = db.class_tests.find({}).sort("updated_at", -1)
    rows = await cursor.to_list(length=200)
    counts = await _attempt_counts([str(row["_id"]) for row in rows])
    tests = []
    for row in rows:
        item = _summary(row)
        item["attempt_count"] = counts.get(str(row["_id"]), 0)
        tests.append(item)
    return {"tests": tests}


async def get_test_for_teacher(test_id: str) -> dict:
    doc = await _load_test(test_id)
    doc["attempt_count"] = await (await get_db()).class_attempts.count_documents({"test_id": str(doc["_id"])})
    return _teacher_test(doc)


def _student_view(test: dict, attempt: dict | None, *, now: datetime) -> dict:
    deadline = as_naive(attempt.get("deadline")) if attempt else None
    open_now = bool(attempt and attempt.get("status") == "in_progress" and isinstance(deadline, datetime) and now <= deadline)
    finished = bool(attempt and attempt.get("status") in _FINAL)
    reveal = bool(finished and test.get("show_answers_after_submit"))
    show_questions = open_now or finished
    source = present_questions(test.get("questions") or [], attempt.get("layout") if attempt else None)
    questions = [public_question(question, reveal=reveal) for question in source] if show_questions else []
    results = [public_result(item, reveal=reveal) for item in (attempt.get("results") or [])] if finished else []
    return {
        "test_id": str(test["_id"]),
        "attempt_id": None if attempt is None else str(attempt["_id"]),
        "title": test.get("title") or "",
        "description": test.get("description") or "",
        "topic": test.get("topic") or "general",
        "test_type": test.get("test_type") or "mixed",
        "duration_minutes": int(test.get("duration_minutes") or 0),
        "question_count": len(test.get("questions") or []),
        "started_at": iso(attempt.get("started_at")) if attempt else None,
        "deadline": iso(attempt.get("deadline")) if attempt else None,
        "submitted_at": iso(attempt.get("submitted_at")) if attempt else None,
        "server_now": iso(now),
        "status": attempt.get("status") if attempt else "not_started",
        "score": attempt.get("score") if attempt else None,
        "time_taken_seconds": attempt.get("time_taken_seconds") if attempt else None,
        "show_answers": reveal,
        "available_from": iso(test.get("available_from")),
        "available_until": iso(test.get("available_until")),
        "phase": _phase(test, attempt, now),
        "allow_retake": bool(test.get("allow_retake")),
        "can_start": bool(test.get("published")) and _in_window(test, now) and not open_now and (not finished or bool(test.get("allow_retake"))),
        "can_resume": open_now,
        "questions": questions,
        "answers": list(attempt.get("answers") or []) if show_questions else [],
        "results": results,
    }


async def list_tests_for_student(user_id: str, *, include_upcoming: bool = False) -> dict:
    now = utcnow()
    db = await get_db()
    cursor = db.class_attempts.find({"user_id": user_id})
    attempts = await cursor.to_list(length=500)
    by_test: dict[str, list] = {}
    for attempt in attempts:
        by_test.setdefault(attempt.get("test_id"), []).append(attempt)
    for rows in by_test.values():
        rows.sort(key=lambda row: as_naive(row.get("started_at")) or now, reverse=True)
    published = await db.class_tests.find({"published": True}).sort("updated_at", -1).to_list(length=200)
    seen = set()
    tests = []
    for doc in published:
        has_attempt = str(doc["_id"]) in by_test
        if not _in_window(doc, now) and not has_attempt:
            start = as_naive(doc.get("available_from"))
            upcoming = isinstance(start, datetime) and now < start
            if not (include_upcoming and upcoming):
                continue
        seen.add(str(doc["_id"]))
        attempt = _pick_attempt(by_test.get(str(doc["_id"]), []))
        if attempt and attempt.get("status") == "in_progress" and now > as_naive(attempt.get("deadline")):
            attempt = await _close(doc, attempt, status="expired", now=now)
        item = _summary(doc)
        item["can_start"] = _in_window(doc, now) and not (
            attempt and attempt.get("status") == "in_progress"
        ) and not (attempt and attempt.get("status") in _FINAL and not doc.get("allow_retake"))
        item["can_resume"] = bool(attempt and attempt.get("status") == "in_progress")
        item["phase"] = _phase(doc, attempt, now)
        item["attempt"] = None if attempt is None else _attempt_summary(attempt)
        tests.append(item)
    # Attempts whose test was later unpublished still show, so the student can read the result.
    missing = [test_id for test_id in by_test if test_id not in seen]
    if missing:
        oids = [as_object_id(test_id) for test_id in missing]
        oids = [oid for oid in oids if oid is not None]
        extras = await db.class_tests.find({"_id": {"$in": oids}}).to_list(length=200)
        for doc in extras:
            attempt = _pick_attempt(by_test.get(str(doc["_id"]), []))
            item = _summary(doc)
            item["can_start"] = False
            item["can_resume"] = bool(attempt and attempt.get("status") == "in_progress" and now <= as_naive(attempt.get("deadline")))
            item["phase"] = _phase(doc, attempt, now)
            item["attempt"] = None if attempt is None else _attempt_summary(attempt)
            tests.append(item)
    return {"tests": tests, "server_now": iso(now)}


async def student_test(user_id: str, test_id: str) -> dict:
    test = await _load_test(test_id)
    rows = await _attempts_for(str(test["_id"]), user_id)
    attempt = _pick_attempt(rows)
    now = utcnow()
    if attempt and attempt.get("status") == "in_progress" and now > as_naive(attempt.get("deadline")):
        attempt = await _close(test, attempt, status="expired", now=now)
    if attempt is None and not test.get("published"):
        raise ClassTestError(404, "Test not found")
    return _student_view(test, attempt, now=now)


def _clean_answers(test: dict, answers) -> list[dict]:
    if answers is None:
        return []
    if not isinstance(answers, list):
        raise ClassTestError(422, "answers must be a list")
    known = {question["id"]: question for question in test.get("questions") or []}
    cleaned = []
    for item in answers[:40]:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        question = known.get(qid)
        if question is None:
            continue
        entry = {"question_id": qid}
        if question["type"] == "mcq":
            selected = item.get("selected")
            entry["selected"] = None if selected is None else str(selected)[:300]
        elif question["type"] == "short":
            text = item.get("text", item.get("answer"))
            entry["text"] = "" if text is None else str(text)[:_MAX_TEXT]
        else:
            code = item.get("code")
            entry["code"] = "" if code is None else str(code)[:_MAX_CODE]
            entry["language"] = "python"
        cleaned.append(entry)
    return cleaned


async def _close(test: dict, attempt: dict, *, status: str, now: datetime, answers: list | None = None) -> dict:
    if attempt.get("status") in _FINAL:
        return attempt
    stored = answers if answers is not None else list(attempt.get("answers") or [])
    report = grade_questions(test.get("questions") or [], stored)
    started = as_naive(attempt.get("started_at")) or now
    deadline = as_naive(attempt.get("deadline")) or now
    end = deadline if status == "expired" or now > deadline else now
    if end < started:
        end = started
    taken = int((end - started).total_seconds())
    summary = summarise_attempt(report["results"])
    db = await get_db()
    saved = await db.class_attempts.find_one_and_update(
        {"_id": attempt["_id"], "status": "in_progress"},
        {
            "$set": {
                "status": status,
                "answers": stored,
                "score": report["score"],
                "results": report["results"],
                "submitted_at": now,
                "time_taken_seconds": taken,
                "weak_topics": summary["weak_topics"],
                "mistake_patterns": summary["mistake_patterns"],
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if saved is None:
        return await db.class_attempts.find_one({"_id": attempt["_id"]})
    await apply_attempt(
        attempt["user_id"],
        "",
        summary["weak_topics"],
        summary["mistake_patterns"],
        report["score"],
        str(attempt["_id"]),
    )
    topic = summary["weak_topics"][0] if summary["weak_topics"] else (test.get("topic") or "general")
    await add_activity(
        attempt["user_id"],
        "class_test_submit",
        {
            "class_test_id": str(test["_id"]),
            "attempt_id": str(attempt["_id"]),
            "score": report["score"],
            "topic": topic,
            "title": test.get("title") or "",
            "error_type": (summary["mistake_patterns"][0].split(":", 1)[0] if summary["mistake_patterns"] else None),
        },
    )
    return saved


async def start_attempt(user_id: str, test_id: str) -> dict:
    test = await _load_test(test_id)
    now = utcnow()
    rows = await _attempts_for(str(test["_id"]), user_id)
    open_attempt = next((row for row in rows if row.get("status") == "in_progress"), None)
    if open_attempt is not None:
        if now > as_naive(open_attempt.get("deadline")):
            await _close(test, open_attempt, status="expired", now=now)
            raise ClassTestError(409, "Time is up")
        return _student_view(test, open_attempt, now=now)
    finished = next((row for row in rows if row.get("status") in _FINAL), None)
    if finished is not None and not test.get("allow_retake"):
        raise ClassTestError(409, "You have already taken this test")
    if not test.get("published") or not _in_window(test, now):
        raise ClassTestError(404, "Test not found")
    deadline = now + timedelta(minutes=int(test.get("duration_minutes") or 1))
    db = await get_db()
    attempt_id = ObjectId()
    doc = {
        "_id": attempt_id,
        "test_id": str(test["_id"]),
        "user_id": user_id,
        "started_at": now,
        "deadline": deadline,
        "status": "in_progress",
        "answers": [],
        "saved_at": None,
        "submitted_at": None,
        "score": None,
        "results": [],
        "time_taken_seconds": None,
        "focus_loss_count": 0,
        "layout": build_layout(test, str(attempt_id)),
    }
    await db.class_attempts.insert_one(doc)
    await add_activity(
        user_id,
        "class_test_start",
        {"class_test_id": str(test["_id"]), "attempt_id": str(doc["_id"]), "title": test.get("title") or ""},
    )
    return _student_view(test, doc, now=now)


async def save_answers(user_id: str, test_id: str, answers) -> dict:
    test = await _load_test(test_id)
    rows = await _attempts_for(str(test["_id"]), user_id)
    attempt = next((row for row in rows if row.get("status") == "in_progress"), None)
    if attempt is None:
        raise ClassTestError(404, "Start the test before saving answers")
    now = utcnow()
    if now > as_naive(attempt.get("deadline")):
        await _close(test, attempt, status="expired", now=now)
        raise ClassTestError(409, "Time is up")
    cleaned = _clean_answers(test, answers)
    db = await get_db()
    result = await db.class_attempts.update_one(
        {"_id": attempt["_id"], "status": "in_progress"},
        {"$set": {"answers": cleaned, "saved_at": now}},
    )
    if result.matched_count == 0:
        raise ClassTestError(409, "Time is up")
    return {"saved": True, "deadline": iso(attempt.get("deadline")), "server_now": iso(now)}


async def record_focus_loss(user_id: str, test_id: str) -> dict:
    """Count one tab switch or focus loss on the open attempt. Capped at 200."""
    test = await _load_test(test_id)
    rows = await _attempts_for(str(test["_id"]), user_id)
    attempt = next((row for row in rows if row.get("status") == "in_progress"), None)
    if attempt is None:
        raise ClassTestError(404, "Start the test before it can record focus")
    now = utcnow()
    if now > as_naive(attempt.get("deadline")):
        await _close(test, attempt, status="expired", now=now)
        raise ClassTestError(409, "Time is up")
    current = int(attempt.get("focus_loss_count") or 0)
    if current >= 200:
        return {"focus_loss_count": current}
    db = await get_db()
    saved = await db.class_attempts.find_one_and_update(
        {"_id": attempt["_id"], "status": "in_progress"},
        {"$inc": {"focus_loss_count": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if saved is None:
        raise ClassTestError(409, "Time is up")
    return {"focus_loss_count": int(saved.get("focus_loss_count") or 0)}


async def run_question(user_id: str, test_id: str, body: dict) -> dict:
    test = await _load_test(test_id)
    rows = await _attempts_for(str(test["_id"]), user_id)
    attempt = next((row for row in rows if row.get("status") == "in_progress"), None)
    if attempt is None:
        raise ClassTestError(404, "Start the test before running code")
    now = utcnow()
    if now > as_naive(attempt.get("deadline")):
        await _close(test, attempt, status="expired", now=now)
        raise ClassTestError(409, "Time is up")
    qid = str(body.get("question_id") or "").strip()
    question = next((item for item in test.get("questions") or [] if item["id"] == qid), None)
    if question is None or question.get("type") != "coding":
        raise ClassTestError(404, "Coding question not found")
    code = body.get("code")
    if code is None or not str(code).strip():
        raise ClassTestError(422, "Write some Python before running it")
    if len(str(code)) > _MAX_CODE:
        raise ClassTestError(422, "That code is too long")
    cases = run_visible(question, str(code), "python")
    return {"question_id": qid, "cases": cases}


async def submit_attempt(user_id: str, test_id: str, answers) -> dict:
    test = await _load_test(test_id)
    rows = await _attempts_for(str(test["_id"]), user_id)
    attempt = _pick_attempt(rows)
    if attempt is None:
        raise ClassTestError(404, "Start the test before submitting")
    now = utcnow()
    if attempt.get("status") == "in_progress":
        if now > as_naive(attempt.get("deadline")):
            attempt = await _close(test, attempt, status="expired", now=now)
        else:
            stored = _clean_answers(test, answers) if answers is not None else list(attempt.get("answers") or [])
            attempt = await _close(test, attempt, status="submitted", now=now, answers=stored)
    return _student_view(test, attempt, now=now)


async def attempts_for_teacher(test_id: str) -> dict:
    test = await _load_test(test_id)
    db = await get_db()
    rows = await db.class_attempts.find({"test_id": str(test["_id"])}).sort("started_at", -1).to_list(length=500)
    oids = []
    for row in rows:
        oid = as_object_id(row.get("user_id"))
        if oid is not None:
            oids.append(oid)
    users = {}
    if oids:
        async for user in db.users.find({"_id": {"$in": oids}}, {"name": 1, "email": 1}):
            users[str(user["_id"])] = user
    attempts = []
    scored = []
    for row in rows:
        user = users.get(row.get("user_id") or "", {})
        if row.get("score") is not None:
            scored.append(float(row["score"]))
        attempts.append(
            {
                "id": str(row["_id"]),
                "student": {
                    "id": row.get("user_id"),
                    "name": user.get("name") or "Student",
                    "email": user.get("email") or "",
                },
                "status": row.get("status"),
                "score": row.get("score"),
                "started_at": iso(row.get("started_at")),
                "deadline": iso(row.get("deadline")),
                "submitted_at": iso(row.get("submitted_at")),
                "time_taken_seconds": row.get("time_taken_seconds"),
                "focus_loss_count": int(row.get("focus_loss_count") or 0),
                "answers": list(row.get("answers") or []),
                "results": list(row.get("results") or []),
            }
        )
    average = round(sum(scored) / len(scored), 1) if scored else None
    test["attempt_count"] = len(attempts)
    return {
        "test": _teacher_test(test),
        "count": len(attempts),
        "submitted": sum(1 for row in attempts if row["status"] in _FINAL),
        "average_score": average,
        "question_stats": _question_stats(test, attempts),
        "attempts": attempts,
    }


def _question_stats(test: dict, attempts: list[dict]) -> list[dict]:
    finished = [row for row in attempts if row.get("status") in _FINAL]
    stats = []
    for question in test.get("questions") or []:
        correct = 0
        graded = 0
        for attempt in finished:
            result = next((item for item in attempt.get("results") or [] if item.get("question_id") == question.get("id")), None)
            if result is None:
                continue
            graded += 1
            if result.get("correct"):
                correct += 1
        percent = round(100.0 * correct / graded, 1) if graded else None
        stats.append(
            {
                "question_id": question.get("id"),
                "type": question.get("type"),
                "skill": question.get("skill") or "general",
                "prompt": str(question.get("prompt") or "")[:180],
                "graded": graded,
                "correct": correct,
                "percent_correct": percent,
            }
        )
    return stats


def _csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if text[:1] in "=+-@\t":
        text = "'" + text
    return text


def attempts_csv(report: dict) -> str:
    """One row per attempt. Scores only; answer text stays in the JSON review."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["student_name", "student_email", "status", "score", "time_taken_seconds", "focus_loss_count", "submitted_at"])
    for attempt in report.get("attempts") or []:
        student = attempt.get("student") or {}
        writer.writerow(
            [
                _csv_cell(student.get("name") or ""),
                _csv_cell(student.get("email") or ""),
                _csv_cell(attempt.get("status") or ""),
                "" if attempt.get("score") is None else attempt.get("score"),
                "" if attempt.get("time_taken_seconds") is None else attempt.get("time_taken_seconds"),
                int(attempt.get("focus_loss_count") or 0),
                _csv_cell(attempt.get("submitted_at") or ""),
            ]
        )
    return buffer.getvalue()
