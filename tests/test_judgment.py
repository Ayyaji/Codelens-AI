"""Judgment rules. These lock the existing full / hint / gentle / break behavior."""

from datetime import datetime, timedelta

from rag_core.db import connection
from rag_core.judgment import (
    extract_error_type,
    extract_topic,
    get_student_context,
    judge_response_level,
)


def _remember(student_id, query, error_type, topic, minutes_ago):
    timestamp = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions
                (student_id, query, agent_used, response_time, timestamp, error_type, topic)
            VALUES (?, ?, 'debug', 0.1, ?, ?, ?)
            """,
            (student_id, query, timestamp, error_type, topic),
        )


def _judge(student_id, query, agent="concept", topic=None):
    return judge_response_level(query, agent, get_student_context(student_id), topic=topic)


def test_extracts_error_and_topic_without_a_model():
    assert extract_error_type("I'm getting NameError: name 'x' is not defined") == "NameError"
    assert extract_error_type("What is a hash map?") is None
    assert extract_topic("How do while loops work?") == "loops"


def test_fresh_student_gets_a_full_explanation():
    assert _judge("fresh", "What is a hash map?") == "full"


def test_fresh_student_gets_full_even_if_they_asked_the_hint_agent():
    assert _judge("fresh-hint", "Give me a hint", agent="hint") == "full"


def test_second_occurrence_of_an_error_is_a_hint():
    _remember("s-hint", "NameError: x", "NameError", None, minutes_ago=5)
    assert _judge("s-hint", "NameError again on x") == "hint"


def test_same_recent_topic_is_gentle():
    _remember("s-gentle", "for loops", None, "loops", minutes_ago=2)
    assert _judge("s-gentle", "How do while loops work?") == "gentle"


def test_error_rule_wins_over_a_recent_topic():
    _remember("s-order", "NameError in a loop", "NameError", "loops", minutes_ago=2)
    assert _judge("s-order", "NameError inside my loop") == "hint"


def test_three_repeats_is_stuck_and_gets_the_full_explanation():
    for minutes in (1, 2, 3):
        _remember("s-stuck", "NameError", "NameError", None, minutes_ago=minutes)
    assert _judge("s-stuck", "NameError again") == "full"


def test_four_logged_errors_suggest_a_break():
    for minutes in (1, 2, 3, 4):
        _remember("s-break", "NameError", "NameError", None, minutes_ago=minutes)
    assert _judge("s-break", "NameError again") == "break"


def test_five_queries_in_ten_minutes_is_treated_as_stuck():
    for minutes in (1, 2, 3, 4, 5):
        _remember("s-pace", "binary trees", None, None, minutes_ago=minutes)
    assert _judge("s-pace", "What is a binary tree?") == "full"


def test_explicit_hint_agent_is_honoured_when_no_earlier_rule_matches():
    _remember("s-ask", "What is Docker?", None, None, minutes_ago=4)
    assert _judge("s-ask", "What is a binary tree?", agent="hint") == "hint"


def test_topic_override_lets_interview_skills_use_the_same_rules():
    _remember("s-sql", "joins", None, "SQL", minutes_ago=3)
    assert _judge("s-sql", "I am practising SQL", topic="SQL") == "gentle"
