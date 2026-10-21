"""Write a guidance or practice turn so the judgment layer can see it later."""

from datetime import datetime

from rag_core.judgment import extract_error_type, extract_topic
from rag_core.store import add_activity

_MISSING = object()


async def log_session(
    student_id: str,
    query: str,
    agent_used: str,
    response_time: float,
    error_type=_MISSING,
    topic=_MISSING,
    activity_type: str = "ask",
    directive: str | None = None,
    when: datetime | None = None,
    extra: dict | None = None,
):
    """Log one turn. Error type and topic are inferred from the query unless provided."""
    if error_type is _MISSING:
        error_type = extract_error_type(query)
    if topic is _MISSING:
        topic = extract_topic(query)
    detail = {
        "query": query,
        "agent_used": agent_used,
        "response_time": response_time,
        "error_type": error_type,
        "topic": topic,
        "directive": directive,
    }
    if extra:
        for key, value in extra.items():
            if key not in detail:
                detail[key] = value
    await add_activity(student_id, activity_type, detail, ts=when)
