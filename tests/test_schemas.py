"""The API models reject blank payloads and keep the response contract."""

import pytest
from pydantic import ValidationError

from rag_core.schemas import (
    AskRequest,
    AskResponse,
    GenerateTestRequest,
    Guidance,
    JDAnalysisResponse,
    RunRequest,
    RunResponse,
    Skill,
    SubmitTestRequest,
    SubmitTestResponse,
)


def test_ask_requires_a_query_and_ignores_a_client_student_id():
    with pytest.raises(ValidationError):
        AskRequest.model_validate({})
    with pytest.raises(ValidationError):
        AskRequest(query="   ")
    parsed = AskRequest.model_validate(
        {"student_id": " s1 ", "query": " Why IndexError? ", "chat_id": "  "}
    )
    assert parsed.query == "Why IndexError?"
    assert parsed.chat_id is None
    assert not hasattr(parsed, "student_id")


def test_ask_response_carries_the_guidance_contract():
    response = AskResponse(
        answer="Define it first.",
        agent_used="debug",
        directive="hint",
        chat_id="abc",
    )
    dumped = response.model_dump()
    assert set(dumped) == {"answer", "agent_used", "directive", "chat_id"}
    assert dumped["answer"] == "Define it first."
    assert dumped["directive"] == "hint"
    with pytest.raises(ValidationError):
        AskResponse(answer="x", agent_used="debug", directive="FULL", chat_id="abc")


def test_run_contract_is_stdout_and_stderr_only():
    with pytest.raises(ValidationError):
        RunRequest(code="  ", language="python")
    parsed = RunRequest(code="print(1)", stdin=None)
    assert parsed.stdin == ""
    kept = RunRequest(code="print(1)", stdin="2\n")
    assert kept.stdin == "2\n"
    response = RunResponse(stdout="2\n", stderr="")
    assert set(response.model_dump()) == {"stdout", "stderr"}


def test_submit_contract():
    with pytest.raises(ValidationError):
        SubmitTestRequest.model_validate({"student_id": "s", "jd_id": "j"})
    parsed = SubmitTestRequest.model_validate(
        {"student_id": "ignored", "jd_id": " j ", "answers": [{"question_id": "q1", "selected": "A"}]}
    )
    assert parsed.jd_id == "j"
    assert not hasattr(parsed, "student_id")
    response = SubmitTestResponse(
        score=50,
        weak_topics=["SQL"],
        guidance=Guidance(
            directive="full",
            message="Read the join explanation.",
            next_steps=["Write three joins"],
            mistake_patterns=["concept_gap:SQL"],
        ),
    )
    dumped = response.model_dump()
    assert set(dumped) == {"score", "weak_topics", "guidance"}
    assert dumped["guidance"]["directive"] == "full"
    with pytest.raises(ValidationError):
        SubmitTestResponse(score=101, weak_topics=[], guidance=Guidance(
            directive="full", message="x", next_steps=[]
        ))


def test_analysis_shape_requires_an_explanation():
    with pytest.raises(ValidationError):
        Skill(name="Python", level="intermediate")
    parsed = JDAnalysisResponse.model_validate(
        {
            "skills": [
                {
                    "name": "Python",
                    "level": "intermediate",
                    "explanation": "The posting uses Python for the service code.",
                }
            ],
            "roadmap": [
                {
                    "order": 1,
                    "skill": "Python",
                    "goal": "Write small scripts confidently",
                    "practice": "Solve two stdin problems",
                }
            ],
        }
    )
    assert parsed.skills[0].name == "Python"
    assert parsed.roadmap[0].practice.startswith("Solve")


def test_generate_request_rejects_a_blank_id():
    with pytest.raises(ValidationError):
        GenerateTestRequest(jd_id=" ")
