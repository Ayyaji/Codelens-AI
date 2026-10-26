"""Decide how much help a student should get right now.

Directives, in the order the rules are applied:

- full: no recent history, or the student is stuck and still needs the whole explanation
- hint: this error is already in their recent history, and they are not flagged as stuck
- gentle: the question continues a topic from the last few sessions
- break: the same error has already been logged four or more times

The rules themselves are unchanged from the original judgment layer. ``topic`` is an
optional override so interview practice can name a skill the keyword list does not know.
"""

import re
from datetime import timedelta
from typing import Dict, Optional

from rag_core.mongo import as_naive, iso, utcnow
from rag_core.store import judgment_history

ERROR_PATTERNS = {
    "NameError": r"NameError|name.*not defined|undefined variable",
    "IndexError": r"IndexError|index out of range|list index",
    "TypeError": r"TypeError|unsupported operand|type mismatch",
    "ValueError": r"ValueError|invalid value|cannot convert",
    "SyntaxError": r"SyntaxError|invalid syntax|parsing error",
    "IndentationError": r"IndentationError|unexpected indent|indentation",
    "AttributeError": r"AttributeError|has no attribute",
    "KeyError": r"KeyError|key not found|missing key",
    "ImportError": r"ImportError|ModuleNotFoundError|cannot import",
}

TOPIC_PATTERNS = {
    "recursion": r"recursion|recursive|factorial|fibonacci",
    "loops": r"loop|for loop|while loop|iteration",
    "lists": r"list|array|append|index",
    "dictionaries": r"dict|dictionary|key|value",
    "functions": r"function|def|parameter|argument|return",
    "classes": r"class|object|method|attribute|self",
    "strings": r"string|str|concatenat|split|join",
    "files": r"file|open|read|write|close",
}


def extract_error_type(query: str) -> Optional[str]:
    """Extract an error type from text using pattern matching."""
    query_lower = query.lower()
    for error_type, pattern in ERROR_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            return error_type
    return None


def extract_topic(query: str) -> Optional[str]:
    """Extract a known practice topic from text using pattern matching."""
    query_lower = query.lower()
    for topic, pattern in TOPIC_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            return topic
    return None


async def get_student_context(student_id: str, lookback_minutes: int = 30) -> Dict:
    """Recent turns, error counts, topic counts, and whether the student looks stuck.

    The rows come from MongoDB ``activity`` (types ``ask`` and ``test_submit``),
    which replaced the SQLite ``sessions`` table.
    """
    cutoff = utcnow() - timedelta(minutes=lookback_minutes)
    sessions = await judgment_history(student_id, cutoff)

    if not sessions:
        return {
            "recent_sessions": [],
            "error_counts": {},
            "topic_counts": {},
            "time_span_minutes": 0,
            "is_stuck": False,
            "session_count": 0,
        }

    error_counts = {}
    topic_counts = {}
    recent = []
    for row in sessions:
        detail = row.get("detail") or {}
        error_type = detail.get("error_type")
        topic = detail.get("topic")
        if error_type:
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        recent.append(
            {
                "query": detail.get("query") or "",
                "agent": detail.get("agent_used"),
                "error": error_type,
                "topic": topic,
                "time": iso(row.get("ts")),
            }
        )

    newest = as_naive(sessions[0].get("ts"))
    oldest = as_naive(sessions[-1].get("ts"))
    if hasattr(newest, "timestamp") and hasattr(oldest, "timestamp"):
        time_span = (newest - oldest).total_seconds() / 60
    else:
        time_span = 0
    is_stuck = any(count >= 3 for count in error_counts.values()) or (
        len(sessions) >= 5 and time_span < 10
    )

    return {
        "recent_sessions": recent,
        "error_counts": error_counts,
        "topic_counts": topic_counts,
        "time_span_minutes": round(time_span, 1),
        "is_stuck": is_stuck,
        "session_count": len(sessions),
    }


def judge_response_level(
    query: str,
    agent_name: str,
    student_context: Dict,
    topic: str | None = None,
) -> str:
    """Return full, hint, gentle, or break for this student and query."""
    if student_context["session_count"] == 0:
        return "full"

    current_error = extract_error_type(query)
    current_topic = topic or extract_topic(query)

    if student_context["is_stuck"]:
        if current_error and student_context["error_counts"].get(current_error, 0) >= 4:
            return "break"
        return "full"

    if current_error and student_context["error_counts"].get(current_error, 0) >= 1:
        return "hint"

    if current_topic:
        recent_on_topic = [
            item
            for item in student_context["recent_sessions"][:3]
            if item["topic"] == current_topic
        ]
        if recent_on_topic:
            return "gentle"

    if agent_name == "hint":
        return "hint"

    return "full"
