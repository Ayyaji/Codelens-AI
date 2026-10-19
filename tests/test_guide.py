"""Guide reads the profile and lets the judgment layer pick the directive."""

from rag_core.agents.guide import build_guidance
from rag_core.session_logger import log_session


def test_first_attempt_is_a_full_explanation():
    guidance = build_guidance(
        "new-student",
        {"weak_topics": ["SQL"], "mistake_patterns": ["concept_gap:SQL"]},
        failure_explanation="WHERE filters rows.",
        roadmap=[{"order": 1, "skill": "SQL", "goal": "filter rows", "practice": "write three joins"}],
    )
    assert guidance["directive"] == "full"
    assert "WHERE filters rows." in guidance["message"]
    assert guidance["next_steps"] == ["SQL: write three joins"]


def test_break_keeps_the_model_explanation_out_of_the_message():
    for _ in range(4):
        log_session(
            "tired",
            "NameError",
            "guide",
            0.1,
            error_type="NameError",
            topic="Python",
        )
    guidance = build_guidance(
        "tired",
        {"weak_topics": ["Python"], "mistake_patterns": ["NameError:Python"]},
        failure_explanation="SECRET SOLUTION",
    )
    assert guidance["directive"] == "break"
    assert "SECRET" not in guidance["message"]
    assert guidance["next_steps"][0].startswith("Take a short break")


def test_a_repeated_skill_is_gentle():
    log_session("sql-student", "joins", "guide", 0.1, error_type=None, topic="SQL")
    guidance = build_guidance(
        "sql-student",
        {"weak_topics": ["SQL"], "mistake_patterns": ["concept_gap:SQL"]},
        failure_explanation="",
    )
    assert guidance["directive"] == "gentle"
    assert guidance["mistake_patterns"] == ["concept_gap:SQL"]
