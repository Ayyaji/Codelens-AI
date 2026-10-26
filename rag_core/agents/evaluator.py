"""Score a practice test.

MCQs are compared in plain code. Coding answers run in the sandbox against
their test cases. The model is called only to explain failures, and a correct
paper never touches it.
"""

from rag_core.judgment import ERROR_PATTERNS
from rag_core.sandbox.runner import run_code
from rag_core.timing import log_latency


def mcq_correct(question: dict, selected: str | None) -> bool:
    if selected is None or not str(selected).strip():
        return False
    choice = str(selected).strip()
    answer = str(question.get("answer") or "").strip()
    options = question.get("options") or []
    if choice.lower() == answer.lower():
        return True
    if len(choice) == 1 and choice.upper() in "ABCD":
        index = ord(choice.upper()) - ord("A")
        if 0 <= index < len(options) and str(options[index]).strip().lower() == answer.lower():
            return True
    return False


def _mistake_from_run(run: dict) -> str:
    if run.get("timed_out"):
        return "timeout"
    stderr = run.get("stderr") or ""
    for name in ERROR_PATTERNS:
        if name in stderr:
            return name
    if stderr.strip() or run.get("exit_code") not in (0, None):
        return "runtime_error"
    return "wrong_output"


def score_coding(question: dict, code: str | None, language: str | None, timeout: float) -> dict:
    cases = question.get("test_cases") or []
    if not code or not str(code).strip():
        return {"correct": False, "credit": 0.0, "mistake": "unanswered", "detail": "No code submitted"}
    lang = language or question.get("language") or "python"
    if lang.strip().lower() not in {"python", "py", "python3"}:
        return {
            "correct": False,
            "credit": 0.0,
            "mistake": "unsupported_language",
            "detail": f"Unsupported language: {lang}",
        }

    passed = 0
    mistake = ""
    detail = ""
    for case in cases:
        stdin = str(case.get("input", case.get("stdin", "")))
        expected = str(case.get("expected", "")).strip()
        run = run_code(code, language=lang, stdin=stdin, timeout=timeout)
        if run["timed_out"] or run["exit_code"] not in (0, None) or run["stdout"].strip() != expected:
            mistake = _mistake_from_run(run)
            actual = run["stdout"].strip() or "(no output)"
            detail = f"expected {expected!r}, got {actual!r}. {run['stderr'][:400]}".strip()
            if run["timed_out"]:
                break
            continue
        passed += 1
    total = len(cases)
    correct = total > 0 and passed == total and not mistake
    return {
        "correct": correct,
        "credit": (passed / total) if total else 0.0,
        "mistake": "" if correct else (mistake or "wrong_output"),
        "detail": "" if correct else detail,
    }


def explain_failures(items: list[dict]) -> str:
    """Ask the larger model why answers failed. Not called when nothing failed."""
    if not items:
        return ""
    from rag_core.llm import complete_json

    prompt = f"""You explain why an interview-practice answer failed.
Return JSON: {{"explanation": "2 to 4 sentences"}}.
Name the misconception. Do not paste a full working solution.
Failures:
{items}
"""
    try:
        data = complete_json("large", prompt)
        text = str(data.get("explanation") or "").strip()
        return text or "The answer did not match the expected result."
    except Exception as exc:
        from rag_core.llm import AIBusy

        if isinstance(exc, AIBusy):
            raise
        return (
            "The answer did not match the expected result. "
            "Compare your output with the sample and check the edge cases."
        )


def evaluate_questions(
    questions: list[dict],
    answers: list[dict],
    timeout: float = 2.0,
) -> dict:
    """Score every stored question. Unanswered questions count as wrong."""
    with log_latency("evaluator") as info:
        by_id = {str(item.get("question_id")): item for item in answers}
        results = []
        failures = []
        for question in questions:
            submission = by_id.get(question["id"])
            if question["type"] == "mcq":
                selected = None if submission is None else submission.get("selected")
                correct = mcq_correct(question, selected)
                result = {
                    "question_id": question["id"],
                    "skill": question["skill"],
                    "type": "mcq",
                    "correct": correct,
                    "credit": 1.0 if correct else 0.0,
                    "mistake": "" if correct else "concept_gap",
                    "detail": "" if correct else f"Selected {selected!r}",
                }
            else:
                coded = score_coding(
                    question,
                    None if submission is None else submission.get("code"),
                    None if submission is None else submission.get("language"),
                    timeout,
                )
                result = {
                    "question_id": question["id"],
                    "skill": question["skill"],
                    "type": "coding",
                    **coded,
                }
            results.append(result)
            if not result["correct"]:
                failures.append(
                    {
                        "question_id": result["question_id"],
                        "skill": result["skill"],
                        "type": result["type"],
                        "mistake": result["mistake"],
                        "prompt": question.get("prompt", "")[:300],
                        "detail": result.get("detail", "")[:300],
                    }
                )

        earned = sum(item["credit"] for item in results)
        score = round(100.0 * earned / len(results), 1) if results else 0.0
        score = min(100.0, max(0.0, score))
        info["llm"] = "yes" if failures else "no"
        explanation = explain_failures(failures) if failures else ""
        return {
            "score": score,
            "results": results,
            "failure_explanation": explanation,
        }
