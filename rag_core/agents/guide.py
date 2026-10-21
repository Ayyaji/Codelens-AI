"""Guidance from the student profile and the existing judgment layer.

The directive (full / hint / gentle / break) is computed by judgment.py.
This module only chooses the wording and the next practice step. It does not
call a model; failure explanations are produced by the evaluator.
"""

from rag_core.judgment import get_student_context, judge_response_level
from rag_core.timing import log_latency

TEMPLATES = {
    "full": (
        "Here is the complete picture for {topic}. Read it once, then try the "
        "next step without looking back at the answer."
    ),
    "hint": (
        "You have run into {topic} before. Take only this nudge and try again "
        "before reading a full solution."
    ),
    "gentle": (
        "This continues practice you just did on {topic}. Connect the miss to "
        "that earlier attempt."
    ),
    "break": (
        "You have repeated this kind of problem enough times. Step away for a "
        "few minutes. When you come back, do one small {topic} exercise instead "
        "of the whole test."
    ),
}


def _practice_for(skill: str, roadmap: list[dict]) -> str:
    for item in roadmap:
        if str(item.get("skill", "")).casefold() == skill.casefold():
            practice = item.get("practice") or item.get("goal")
            if practice:
                return f"{skill}: {practice}"
    return f"Practise {skill} with one smaller question before retrying the test."


async def build_guidance(
    student_id: str,
    profile: dict,
    failure_explanation: str = "",
    roadmap: list[dict] | None = None,
) -> dict:
    """Combine the latest profile with FULL/HINT/GENTLE/BREAK."""
    with log_latency("guide"):
        roadmap = roadmap or []
        weak = profile.get("weak_topics") or []
        patterns = profile.get("mistake_patterns") or []
        topic = weak[0] if weak else "the next roadmap item"
        pattern_text = " ".join(patterns)
        query = f"I am practising {topic}. {pattern_text}".strip()
        context = await get_student_context(student_id)
        directive = judge_response_level(query, "guide", context, topic=topic if weak else None)

        steps = []
        if directive == "break":
            steps.append("Take a short break before the next attempt.")
        if weak:
            steps.extend(_practice_for(skill, roadmap) for skill in weak)
        else:
            steps.append("Pick the next roadmap item and try a slightly harder question.")

        if not weak and directive != "break":
            message = (
                "Nothing on this attempt looks weak. "
                "Pick the next roadmap item and stretch a little."
            )
        else:
            message = TEMPLATES[directive].format(topic=topic)
            if failure_explanation and directive in {"full", "hint", "gentle"}:
                message = f"{message} {failure_explanation}".strip()

        return {
            "directive": directive,
            "message": message,
            "next_steps": steps,
            "mistake_patterns": patterns,
        }
