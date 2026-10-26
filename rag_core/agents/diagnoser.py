"""Turn a scored attempt into weak topics and mistake patterns.

This is plain counting. The persona written here is what My Space and the
teacher dashboard read. The judgment layer still reads activity, which the
API records after guidance is chosen.
"""

from rag_core.store import apply_attempt, insert_submission, persona_view
from rag_core.timing import log_latency


def summarise_attempt(results: list[dict]) -> dict:
    """Weak topics in first-miss order, and ``mistake:skill`` labels."""
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
    return {"weak_topics": weak, "mistake_patterns": patterns}


async def load_profile(student_id: str, jd_id: str = "") -> dict:
    """Current persona for a student. The profile is per person, not per JD."""
    del jd_id
    view = await persona_view(student_id)
    scores = view.get("scores") or []
    return {
        "weak_topics": view.get("weak_topics") or [],
        "mistake_patterns": view.get("mistake_patterns") or [],
        "last_score": scores[-1]["score"] if scores else None,
    }


async def diagnose(
    student_id: str,
    jd_id: str,
    results: list[dict],
    score: float,
    answers: list | None = None,
) -> dict:
    """Store this attempt's weak topics and the patterns behind the misses."""
    with log_latency("diagnoser"):
        summary = summarise_attempt(results)
        test_id = await insert_submission(
            student_id,
            jd_id,
            score,
            answers or [],
            summary["weak_topics"],
            summary["mistake_patterns"],
        )
        await apply_attempt(
            student_id,
            jd_id,
            summary["weak_topics"],
            summary["mistake_patterns"],
            score,
            test_id,
        )
        return {
            "weak_topics": summary["weak_topics"],
            "mistake_patterns": summary["mistake_patterns"],
            "last_score": score,
            "test_id": test_id,
        }
