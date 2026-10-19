"""Write a guidance or practice turn so the judgment layer can see it later."""

from datetime import datetime

from rag_core.db import connection, init_db
from rag_core.judgment import extract_error_type, extract_topic

_MISSING = object()


def log_session(
    student_id: str,
    query: str,
    agent_used: str,
    response_time: float,
    error_type=_MISSING,
    topic=_MISSING,
):
    """Log one turn. Error type and topic are inferred from the query unless provided."""
    if error_type is _MISSING:
        error_type = extract_error_type(query)
    if topic is _MISSING:
        topic = extract_topic(query)

    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions
                (student_id, query, agent_used, response_time, timestamp, error_type, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                query,
                agent_used,
                response_time,
                datetime.now().isoformat(),
                error_type,
                topic,
            ),
        )
