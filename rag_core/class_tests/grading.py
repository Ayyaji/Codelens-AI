"""Score a class test without touching the JD evaluator's question shape.

MCQs are compared in code. Coding answers run in the existing sandbox, and
the score is the fraction of hidden cases that pass. Short answers match
keywords, and call the larger model only when a key is configured and the
keyword check missed.
"""

import os

from rag_core.sandbox.runner import run_code

_HIDDEN_KEYS = ("correct_index", "answer", "expected", "keywords", "hidden_cases", "explanation")


def llm_available() -> bool:
    """True when a short-answer miss may ask the model.

    The test suite sets ``CODELENS_MONGO_MOCK`` and has no key, so grading
    stays on the keyword path there.
    """
    if os.getenv("CODELENS_MONGO_MOCK") == "1":
        return False
    if os.getenv("CODELENS_SHORT_ANSWER_LLM", "1").strip() == "0":
        return False
    from rag_core.llm import get_api_key

    return bool(get_api_key())


def _blank(question: dict, mistake: str, detail: str) -> dict:
    return {
        "question_id": question["id"],
        "skill": question.get("skill") or "general",
        "type": question.get("type"),
        "correct": False,
        "credit": 0.0,
        "mistake": mistake,
        "detail": detail,
    }


def _hit(question: dict, detail: str = "") -> dict:
    return {
        "question_id": question["id"],
        "skill": question.get("skill") or "general",
        "type": question.get("type"),
        "correct": True,
        "credit": 1.0,
        "mistake": "",
        "detail": detail,
    }


def score_mcq(question: dict, selected) -> dict:
    options = [str(option) for option in question.get("options") or []]
    try:
        correct_index = int(question.get("correct_index"))
    except (TypeError, ValueError):
        correct_index = -1
    if selected is None or (isinstance(selected, str) and not selected.strip()):
        return _blank(question, "unanswered", "No option selected")
    text = str(selected).strip()
    if text.isdigit() and int(text) == correct_index:
        return _hit(question)
    if len(text) == 1 and text.upper() in "ABCD" and ord(text.upper()) - ord("A") == correct_index:
        return _hit(question)
    if 0 <= correct_index < len(options) and text.lower() == options[correct_index].strip().lower():
        return _hit(question)
    return _blank(question, "concept_gap", f"Selected {text!r}")


def _keyword_match(question: dict, text: str) -> bool:
    folded = " ".join(text.lower().split())
    if not folded:
        return False
    expected = " ".join(str(question.get("expected") or "").lower().split())
    keywords = [
        " ".join(str(word).lower().split())
        for word in (question.get("keywords") or [])
        if str(word).strip()
    ]
    if expected and (folded == expected or expected in folded):
        return True
    if keywords and all(word in folded for word in keywords):
        return True
    return False


def _llm_short(question: dict, text: str) -> bool | None:
    from rag_core.llm import complete_json

    prompt = f"""You grade one short interview answer.
Return JSON: {{"correct": true or false}}.
Mark it correct only when the answer states the same fact as the expected answer.
Do not require the same wording. A wrong fact is false.
Question: {question.get("prompt", "")[:800]}
Expected: {question.get("expected", "")}
Keywords: {question.get("keywords") or []}
Student: {text[:800]}
"""
    try:
        data = complete_json("large", prompt)
    except Exception as exc:
        from rag_core.llm import AIBusy

        if isinstance(exc, AIBusy):
            raise
        return None
    if isinstance(data, dict) and isinstance(data.get("correct"), bool):
        return data["correct"]
    return None


def score_short(question: dict, text) -> dict:
    answer = "" if text is None else str(text).strip()
    if not answer:
        return _blank(question, "unanswered", "No answer submitted")
    if _keyword_match(question, answer):
        return _hit(question, "Keyword match")
    if llm_available():
        judged = _llm_short(question, answer)
        if judged is True:
            return _hit(question, "Model accepted the wording")
        if judged is False:
            return _blank(question, "concept_gap", "The answer missed the expected idea")
    return _blank(question, "keyword_miss", "The answer did not include the expected wording")


def _passed_case(code: str, language: str, case: dict, timeout: float) -> tuple[bool, dict]:
    run = run_code(code, language=language, stdin=str(case.get("stdin", "")), timeout=timeout)
    expected = str(case.get("expected", "")).strip()
    actual = (run.get("stdout") or "").strip()
    ok = not run.get("timed_out") and run.get("exit_code") in (0, None) and actual == expected
    return ok, run


def score_coding(question: dict, code, language, timeout: float = 2.0) -> dict:
    hidden = list(question.get("hidden_cases") or [])
    visible = list(question.get("visible_cases") or [])
    cases = hidden or visible
    if code is None or not str(code).strip():
        return _blank(question, "unanswered", "No code submitted")
    lang = language or question.get("language") or "python"
    if not cases:
        return _blank(question, "wrong_output", "This question has no test cases")
    passed = 0
    mistake = ""
    detail = ""
    for case in cases:
        ok, run = _passed_case(str(code), lang, case, timeout)
        if ok:
            passed += 1
            continue
        if run.get("timed_out"):
            mistake = "timeout"
        elif (run.get("stderr") or "").strip() or run.get("exit_code") not in (0, None):
            mistake = "runtime_error"
        else:
            mistake = "wrong_output"
        actual = (run.get("stdout") or "").strip() or "(no output)"
        expected = str(case.get("expected", "")).strip()
        detail = f"expected {expected!r}, got {actual!r}"
        if run.get("timed_out"):
            break
    total = len(cases)
    credit = round(passed / total, 4) if total else 0.0
    correct = total > 0 and passed == total
    return {
        "question_id": question["id"],
        "skill": question.get("skill") or "general",
        "type": "coding",
        "correct": correct,
        "credit": 1.0 if correct else credit,
        "mistake": "" if correct else (mistake or "wrong_output"),
        "detail": "" if correct else detail,
        "passed": passed,
        "total": total,
    }


def grade_questions(questions: list[dict], answers: list[dict], timeout: float = 2.0) -> dict:
    """Score every question. Missing answers are wrong. Score is 0–100."""
    by_id = {}
    for item in answers or []:
        if isinstance(item, dict) and item.get("question_id"):
            by_id[str(item["question_id"])] = item
    results = []
    for question in questions:
        submission = by_id.get(question["id"])
        kind = question.get("type")
        if kind == "mcq":
            selected = None if submission is None else submission.get("selected")
            result = score_mcq(question, selected)
        elif kind == "short":
            text = None if submission is None else submission.get("text", submission.get("answer"))
            result = score_short(question, text)
        else:
            result = score_coding(
                question,
                None if submission is None else submission.get("code"),
                None if submission is None else submission.get("language"),
                timeout,
            )
        results.append(result)
    earned = sum(float(item["credit"]) for item in results)
    score = round(100.0 * earned / len(results), 1) if results else 0.0
    score = min(100.0, max(0.0, score))
    return {"score": score, "results": results}


def run_visible(question: dict, code: str, language: str | None, timeout: float = 2.0) -> list[dict]:
    """Run the student's code against visible cases only."""
    lang = language or question.get("language") or "python"
    cases = []
    for index, case in enumerate(question.get("visible_cases") or []):
        ok, run = _passed_case(code, lang, case, timeout)
        cases.append(
            {
                "index": index,
                "stdin": str(case.get("stdin", "")),
                "expected": str(case.get("expected", "")).strip(),
                "stdout": run.get("stdout") or "",
                "stderr": run.get("stderr") or "",
                "passed": ok,
                "timed_out": bool(run.get("timed_out")),
            }
        )
    return cases


def public_question(question: dict, *, reveal: bool) -> dict:
    """Student view. Hidden cases and the key stay off unless ``reveal``."""
    kind = question.get("type")
    out = {
        "id": question["id"],
        "type": kind,
        "skill": question.get("skill") or "general",
        "prompt": question.get("prompt") or "",
    }
    if kind == "mcq":
        out["options"] = list(question.get("options") or [])
        if reveal:
            out["correct_index"] = question.get("correct_index")
            options = out["options"]
            index = question.get("correct_index")
            if isinstance(index, int) and 0 <= index < len(options):
                out["correct_option"] = options[index]
            out["explanation"] = question.get("explanation") or ""
    elif kind == "short":
        if reveal:
            out["expected"] = question.get("expected") or ""
            out["keywords"] = list(question.get("keywords") or [])
            out["explanation"] = question.get("explanation") or ""
    else:
        out["language"] = question.get("language") or "python"
        out["signature"] = question.get("signature") or ""
        out["starter_code"] = question.get("starter_code") or ""
        out["visible_cases"] = [
            {"stdin": str(case.get("stdin", "")), "expected": str(case.get("expected", "")).strip()}
            for case in question.get("visible_cases") or []
        ]
        if reveal:
            out["explanation"] = question.get("explanation") or ""
    return out


def public_result(result: dict, *, reveal: bool) -> dict:
    shown = {
        "question_id": result.get("question_id"),
        "skill": result.get("skill") or "general",
        "type": result.get("type"),
        "correct": bool(result.get("correct")),
        "credit": float(result.get("credit") or 0),
    }
    if result.get("type") == "coding":
        shown["passed"] = result.get("passed")
        shown["total"] = result.get("total")
    if reveal:
        shown["mistake"] = result.get("mistake") or ""
        shown["detail"] = result.get("detail") or ""
    return shown


def leaks_key(payload: dict) -> bool:
    """Used by tests. A student payload must not carry these keys."""
    return any(key in payload for key in _HIDDEN_KEYS)
