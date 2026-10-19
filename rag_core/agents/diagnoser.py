"""Turn a scored attempt into weak topics and mistake patterns.

This is plain counting. The profile is what the guide reads; the judgment
layer still reads the session history written by the API.
"""

import json
from datetime import datetime

from rag_core.db import connection, init_db
from rag_core.timing import log_latency


def load_profile(student_id: str, jd_id: str) -> dict:
    init_db()
    with connection() as conn:
        row = conn.execute(
            """
            SELECT weak_topics, mistake_patterns, last_score
            FROM student_profile
            WHERE student_id = ? AND jd_id = ?
            """,
            (student_id, jd_id),
        ).fetchone()
    if row is None:
        return {"weak_topics": [], "mistake_patterns": [], "last_score": None}
    return {
        "weak_topics": json.loads(row["weak_topics"]),
        "mistake_patterns": json.loads(row["mistake_patterns"]),
        "last_score": row["last_score"],
    }


def diagnose(student_id: str, jd_id: str, results: list[dict], score: float) -> dict:
    """Store this attempt's weak topics and the patterns behind the misses."""
    with log_latency("diagnoser"):
        weak = []
        patterns = []
        for result in results:
            if result.get("correct"):
                continue
            skill = result.get("skill") or "general"
            if skill not in weak:
                weak.append(skill)
            mistake = result.get("mistake") or "incorrect"
            label = f"{mistake}:{skill}"
            if label not in patterns:
                patterns.append(label)

        now = datetime.now().isoformat()
        init_db()
        with connection() as conn:
            conn.execute(
                """
                INSERT INTO student_profile
                    (student_id, jd_id, weak_topics, mistake_patterns, last_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, jd_id) DO UPDATE SET
                    weak_topics = excluded.weak_topics,
                    mistake_patterns = excluded.mistake_patterns,
                    last_score = excluded.last_score,
                    updated_at = excluded.updated_at
                """,
                (student_id, jd_id, json.dumps(weak), json.dumps(patterns), score, now),
            )
        return {"weak_topics": weak, "mistake_patterns": patterns, "last_score": score}
