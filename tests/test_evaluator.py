"""MCQ scoring is deterministic. The model is only asked to explain failures."""

import logging

from rag_core.agents.evaluator import evaluate_questions, mcq_correct

MCQ = {
    "id": "q1",
    "type": "mcq",
    "skill": "SQL",
    "prompt": "Which clause filters rows?",
    "options": ["SELECT", "WHERE", "ORDER BY", "GROUP BY"],
    "answer": "WHERE",
}
CODING = {
    "id": "c1",
    "type": "coding",
    "skill": "Python",
    "prompt": "Read text and print it back.",
    "language": "python",
    "test_cases": [
        {"input": "ok\n", "expected": "ok"},
        {"input": "slow\n", "expected": "slow"},
    ],
}
ECHO = "import sys\nprint(sys.stdin.read().strip())\n"


def _forbid_llm(monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("the model should not be called")

    monkeypatch.setattr("rag_core.llm.complete_json", explode)


def test_mcq_matches_option_text_or_letter():
    assert mcq_correct(MCQ, "WHERE")
    assert mcq_correct(MCQ, "where")
    assert mcq_correct(MCQ, "B")
    assert not mcq_correct(MCQ, "SELECT")
    assert not mcq_correct(MCQ, None)


def test_perfect_score_does_not_call_the_model(monkeypatch, caplog):
    _forbid_llm(monkeypatch)
    caplog.set_level(logging.INFO, logger="codelens.agents")
    report = evaluate_questions(
        [MCQ, CODING],
        [
            {"question_id": "q1", "selected": "B"},
            {"question_id": "c1", "code": ECHO, "language": "python"},
        ],
    )
    assert report["score"] == 100.0
    assert report["failure_explanation"] == ""
    assert all(item["correct"] for item in report["results"])
    assert any("agent=evaluator" in record.message and "llm=no" in record.message for record in caplog.records)


def test_wrong_mcq_is_a_concept_gap_and_the_model_only_explains(monkeypatch):
    def fake(_size, prompt):
        assert "WHERE" not in prompt or "failed" in prompt or "Failures" in prompt
        assert "full solution" in prompt or "working solution" in prompt
        return {"explanation": "WHERE filters rows."}

    monkeypatch.setattr("rag_core.llm.complete_json", fake)
    report = evaluate_questions(
        [MCQ, CODING],
        [
            {"question_id": "q1", "selected": "SELECT"},
            {"question_id": "c1", "code": ECHO},
        ],
    )
    assert report["score"] == 50.0
    assert report["results"][0]["mistake"] == "concept_gap"
    assert report["results"][1]["correct"] is True
    assert report["failure_explanation"] == "WHERE filters rows."


def test_unanswered_questions_score_zero(monkeypatch):
    monkeypatch.setattr(
        "rag_core.llm.complete_json",
        lambda *_args, **_kwargs: {"explanation": "missing"},
    )
    report = evaluate_questions([MCQ], [])
    assert report["score"] == 0.0
    assert report["results"][0]["mistake"] == "concept_gap"


def test_wrong_output_is_not_a_model_decision(monkeypatch):
    monkeypatch.setattr(
        "rag_core.llm.complete_json",
        lambda *_args, **_kwargs: {"explanation": "You printed the wrong value."},
    )
    report = evaluate_questions(
        [CODING],
        [{"question_id": "c1", "code": "print('nope')\n"}],
    )
    assert report["score"] == 0.0
    assert report["results"][0]["mistake"] == "wrong_output"
    assert report["failure_explanation"] == "You printed the wrong value."


def test_syntax_error_is_classified_from_stderr(monkeypatch):
    monkeypatch.setattr(
        "rag_core.llm.complete_json",
        lambda *_args, **_kwargs: {"explanation": "The function header is incomplete."},
    )
    report = evaluate_questions(
        [{**CODING, "test_cases": [{"input": "", "expected": "1"}]}],
        [{"question_id": "c1", "code": "def (\n"}],
    )
    assert report["results"][0]["mistake"] == "SyntaxError"
    assert report["score"] == 0.0


def test_timeout_stops_the_remaining_cases(monkeypatch):
    monkeypatch.setattr(
        "rag_core.llm.complete_json",
        lambda *_args, **_kwargs: {"explanation": "The program did not finish."},
    )
    code = (
        "import sys, time\n"
        "data = sys.stdin.read().strip()\n"
        "if data == 'slow':\n"
        "    time.sleep(30)\n"
        "print(data)\n"
    )
    report = evaluate_questions(
        [CODING],
        [{"question_id": "c1", "code": code}],
        timeout=0.4,
    )
    assert report["results"][0]["mistake"] == "timeout"
    assert report["results"][0]["credit"] == 0.5
    assert report["score"] == 50.0
