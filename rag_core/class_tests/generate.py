"""Draft MCQs and coding questions from a syllabus.

One Groq call covers a small chunk so a free-tier limit stops the rest of the
batch instead of the whole paper. Coding questions are kept only when a
generated reference solution passes every case in the existing sandbox.
The reference solution is not returned. Nothing is published or stored.
"""

import json
import logging
import re

from rag_core.class_tests.errors import ClassTestError
from rag_core.class_tests.harness import function_name, runner_tail, starter_for
from rag_core.class_tests.service import normalize_question
from rag_core.llm import AIBusy, complete_json

logger = logging.getLogger("codelens.class_tests.generate")

MCQ_CHUNK = 3
_MAX_MCQ = 8
_MAX_CODING = 4
_MAX_CALLS = 16
_DIFFICULTIES = {"easy", "medium", "hard"}
_LANGUAGES = {"python", "py", "python3"}
_SIGNATURE = re.compile(r"^def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(.*\)\s*:?\s*$")
_HARNESS_NOTE = (
    "Write the function in Python and leave the `if __name__` block as it is. "
    "That block reads a JSON list of arguments from stdin and prints the return value. "
    "Bools print as true or false. Lists print as compact JSON."
)


def _spec(body: dict) -> dict:
    if not isinstance(body, dict):
        raise ClassTestError(422, "Send a JSON object")
    syllabus = str(body.get("syllabus") or body.get("topic") or "").strip()
    if len(syllabus) < 2:
        raise ClassTestError(422, "Enter a topic or syllabus")
    if len(syllabus) > 4000:
        raise ClassTestError(422, "The syllabus is longer than 4000 characters")
    difficulty = str(body.get("difficulty") or "medium").strip().lower()
    if difficulty not in _DIFFICULTIES:
        raise ClassTestError(422, "difficulty must be easy, medium, or hard")
    try:
        mcq_count = int(body.get("mcq_count") or 0)
        coding_count = int(body.get("coding_count") or 0)
    except (TypeError, ValueError) as exc:
        raise ClassTestError(422, "Question counts must be whole numbers") from exc
    if mcq_count < 0 or coding_count < 0:
        raise ClassTestError(422, "Question counts cannot be negative")
    if mcq_count > _MAX_MCQ:
        raise ClassTestError(422, f"Generate at most {_MAX_MCQ} MCQs at a time")
    if coding_count > _MAX_CODING:
        raise ClassTestError(422, f"Generate at most {_MAX_CODING} coding questions at a time")
    if mcq_count + coding_count < 1:
        raise ClassTestError(422, "Ask for at least one question")
    language = str(body.get("language") or "python").strip().lower() or "python"
    if coding_count and language not in _LANGUAGES:
        raise ClassTestError(422, "Coding questions can be generated in Python only")
    avoid = []
    raw_avoid = body.get("avoid") or []
    if isinstance(raw_avoid, str):
        raw_avoid = [raw_avoid]
    if not isinstance(raw_avoid, list):
        raise ClassTestError(422, "avoid must be a list of prompts")
    for item in raw_avoid[:8]:
        text = str(item).strip()
        if text:
            avoid.append(text[:300])
    return {
        "syllabus": syllabus,
        "difficulty": difficulty,
        "mcq_count": mcq_count,
        "coding_count": coding_count,
        "language": "python",
        "use_kb": bool(body.get("use_kb")),
        "avoid": avoid,
        "topic": str(body.get("topic") or "").strip()[:60],
    }


def _kb_excerpt(syllabus: str) -> str:
    """Approved-note text for the prompt. Empty when the index is missing."""
    try:
        from rag_core.agents.retrieval import get_context

        text = get_context(syllabus[:500], k=2) or ""
    except Exception as exc:
        logger.warning("class-test generate kb unavailable error_type=%s", type(exc).__name__)
        return ""
    return str(text).strip()[:1500]


def _call(prompt: str, budget: dict) -> dict:
    if budget["n"] >= _MAX_CALLS:
        raise AIBusy()
    budget["n"] += 1
    return complete_json("small", prompt)


def _grounding(spec: dict, context: str) -> str:
    lines = [
        f"Difficulty: {spec['difficulty']}",
        "Syllabus:",
        spec["syllabus"][:3500],
    ]
    if spec["avoid"]:
        lines.append("Do not repeat these questions:")
        lines.extend(f"- {item}" for item in spec["avoid"])
    if context:
        lines.append("Use these approved notes when they apply. Do not copy them verbatim:")
        lines.append(context)
    return "\n".join(lines)


def _mcq_prompt(spec: dict, context: str, count: int) -> str:
    return f"""You write multiple-choice questions for a college programming class.
Return one JSON object and nothing else:
{{"questions":[{{"skill":"short topic","prompt":"...","options":["...","...","...","..."],"correct_index":0,"explanation":"..."}}]}}
KIND: mcq
COUNT: {count}
Rules:
- Exactly {count} questions.
- Each question has exactly 4 distinct options.
- correct_index is 0, 1, 2, or 3 and marks the single correct option.
- Every question has a one or two sentence explanation of the correct option.
- Prompts are specific. No "all of the above".
{_grounding(spec, context)}
"""


def _coding_prompt(spec: dict, context: str) -> str:
    return f"""You write one Python function problem for a college DSA quiz.
Return one JSON object and nothing else:
{{"title":"...","skill":"arrays","statement":"...","constraints":"...","signature":"def name(arg):","explanation":"...","reference_solution":"def name(arg):\\n    return ...","visible_cases":[{{"stdin":"[1, 2]","expected":"3"}}],"hidden_cases":[{{"stdin":"[0, 0]","expected":"0"}}]}}
KIND: coding
COUNT: 1
Rules:
- signature is a single Python def line. The name is a function name.
- reference_solution is only that function. No imports, no input(), no print, no main block.
- stdin is a JSON list of arguments. The harness calls the function with those arguments.
- expected is the exact stdout: numbers as digits, strings without quotes, true or false, lists as compact JSON with no spaces.
- One or two visible cases and two or three hidden cases. Hidden cases differ from the visible ones.
- The reference solution must pass every case.
{_grounding(spec, context)}
"""


def _repair(prompt: str, previous: str, reason: str) -> str:
    return (
        f"{prompt}\nThe previous JSON failed validation: {reason}\n"
        f"Previous JSON (fix it, do not explain):\n{previous[:2500]}\n"
        "Return only the corrected JSON object."
    )


def _as_questions(data) -> list:
    if isinstance(data, dict):
        raw = data.get("questions")
        if isinstance(raw, list):
            return raw
        if "prompt" in data or "signature" in data or "statement" in data:
            return [data]
    return []


def _valid_mcq(raw) -> tuple[dict | None, str]:
    if not isinstance(raw, dict):
        return None, "A question was not an object"
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        return None, "A question is missing its prompt"
    options_raw = raw.get("options")
    if not isinstance(options_raw, list) or len(options_raw) != 4:
        return None, "Each MCQ needs exactly 4 options"
    options = []
    seen = set()
    for option in options_raw:
        text = str(option).strip()
        if not text:
            return None, "An option is blank"
        key = text.lower()
        if key in seen:
            return None, "Options must be distinct"
        seen.add(key)
        options.append(text[:300])
    try:
        correct_index = int(raw.get("correct_index"))
    except (TypeError, ValueError):
        return None, "correct_index must be 0, 1, 2, or 3"
    if not 0 <= correct_index <= 3:
        return None, "correct_index must be 0, 1, 2, or 3"
    explanation = str(raw.get("explanation") or "").strip()
    if not explanation:
        return None, "Each MCQ needs an explanation"
    skill = str(raw.get("skill") or "general").strip() or "general"
    return {
        "type": "mcq",
        "skill": skill[:60],
        "prompt": prompt[:1000],
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation[:800],
    }, ""


def _take_mcqs(data, count: int) -> tuple[list[dict], str]:
    found = []
    reason = "The response had no questions"
    for raw in _as_questions(data):
        question, reason = _valid_mcq(raw)
        if question is None:
            continue
        found.append(question)
        if len(found) == count:
            return found, ""
    if not found:
        return [], reason or "No valid MCQ was returned"
    return found, ""


def _cases(raw, label: str) -> tuple[list[dict], str]:
    if not isinstance(raw, list) or not raw:
        return [], f"{label} need at least one case"
    cases = []
    for case in raw[:4]:
        if not isinstance(case, dict):
            return [], f"{label} must be objects"
        stdin = case.get("stdin", case.get("input", ""))
        stdin = "" if stdin is None else str(stdin).strip()
        expected = case.get("expected", "")
        expected = "" if expected is None else str(expected).strip()
        if not stdin or expected == "":
            return [], f"{label} need stdin and expected"
        if len(stdin) > 500 or len(expected) > 500:
            return [], "A test case is too long"
        try:
            parsed = json.loads(stdin)
        except json.JSONDecodeError:
            return [], "stdin must be a JSON list of arguments"
        if not isinstance(parsed, list):
            return [], "stdin must be a JSON list of arguments"
        cases.append({"stdin": stdin, "expected": expected})
    return cases, ""


def _program(signature: str, solution: str) -> str:
    name = function_name(signature)
    cleaned = solution.strip()
    cleaned = re.sub(r"^```(?:python)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    marker = "\nif __name__"
    if marker in cleaned:
        cleaned = cleaned.split(marker, 1)[0].rstrip()
    if f"def {name}" not in cleaned:
        raise ValueError(f"Reference solution must define {name}")
    if len(cleaned) > 8000:
        raise ValueError("Reference solution is too long")
    return cleaned.rstrip() + "\n" + runner_tail(name)


def _check_reference(signature: str, solution: str, cases: list[dict]) -> str:
    """Empty string when the solution passes every case in the class-test harness."""
    try:
        program = _program(signature, solution)
    except ValueError as exc:
        return str(exc)
    from rag_core.class_tests.grading import _passed_case

    for index, case in enumerate(cases, start=1):
        ok, run = _passed_case(program, "python", case, 2.0)
        if ok:
            continue
        stderr = (run.get("stderr") or "").strip().splitlines()
        tail = stderr[-1][:180] if stderr else ""
        actual = (run.get("stdout") or "").strip() or "(no output)"
        expected = str(case.get("expected") or "").strip()
        extra = f" {tail}" if tail else ""
        return f"Case {index} failed. expected {expected!r}, got {actual!r}.{extra}"
    return ""


def _valid_coding(raw, topic: str) -> tuple[dict | None, str]:
    if not isinstance(raw, dict):
        return None, "The coding question was not an object"
    signature = str(raw.get("signature") or "").strip()
    if not _SIGNATURE.match(signature):
        return None, "signature must be one def line"
    if not signature.endswith(":"):
        signature += ":"
    title = str(raw.get("title") or "").strip()
    statement = str(raw.get("statement") or raw.get("prompt") or "").strip()
    if not statement:
        return None, "The coding question needs a statement"
    constraints = str(raw.get("constraints") or "").strip()
    solution = str(raw.get("reference_solution") or raw.get("solution") or "")
    if not solution.strip():
        return None, "A reference solution is required"
    visible, reason = _cases(raw.get("visible_cases"), "Visible cases")
    if reason:
        return None, reason
    hidden, reason = _cases(raw.get("hidden_cases"), "Hidden cases")
    if reason:
        return None, reason
    visible = visible[:2]
    hidden = hidden[:3]
    failure = _check_reference(signature, solution, visible + hidden)
    if failure:
        return None, failure
    skill = str(raw.get("skill") or topic or "DSA").strip() or "DSA"
    explanation = str(raw.get("explanation") or "").strip()
    prompt = statement
    if title:
        prompt = f"{title}\n\n{statement}"
    if constraints:
        prompt = f"{prompt}\n\nConstraints: {constraints}"
    prompt = f"{prompt}\n\n{_HARNESS_NOTE}"
    return {
        "type": "coding",
        "skill": skill[:60],
        "prompt": prompt[:4000],
        "signature": signature[:200],
        "language": "python",
        "starter_code": starter_for(signature),
        "visible_cases": visible,
        "hidden_cases": hidden,
        "explanation": explanation[:800],
    }, ""


def _normalize_all(raw_questions: list[dict]) -> list[dict]:
    ready = []
    for index, raw in enumerate(raw_questions, start=1):
        allowed = {"mcq"} if raw.get("type") == "mcq" else {"coding"}
        ready.append(normalize_question(raw, index, allowed))
    return ready


def _ask(prompt: str, budget: dict):
    try:
        return _call(prompt, budget), ""
    except AIBusy:
        raise
    except Exception:
        return None, "Response was not JSON"


def _chunk_mcq(spec: dict, context: str, count: int, budget: dict) -> tuple[list[dict], str]:
    prompt = _mcq_prompt(spec, context, count)
    reason = "No valid MCQ was returned"
    previous = ""
    for attempt in range(2):
        data, failed = _ask(prompt if attempt == 0 else _repair(prompt, previous, reason), budget)
        if failed:
            reason = failed
            continue
        found, reason = _take_mcqs(data, count)
        if found:
            return _normalize_all(found), ""
        previous = json.dumps(data)[:2500] if isinstance(data, (dict, list)) else ""
    return [], reason


def _chunk_coding(spec: dict, context: str, budget: dict) -> tuple[dict | None, str]:
    prompt = _coding_prompt(spec, context)
    reason = "No valid coding question was returned"
    previous = ""
    for attempt in range(2):
        data, failed = _ask(prompt if attempt == 0 else _repair(prompt, previous, reason), budget)
        if failed:
            reason = failed
            continue
        raw = data
        if isinstance(data, dict) and isinstance(data.get("questions"), list) and data["questions"]:
            raw = data["questions"][0]
        question, reason = _valid_coding(raw, spec["topic"])
        if question is not None:
            return _normalize_all([question])[0], ""
        previous = json.dumps(data)[:2500] if isinstance(data, (dict, list)) else ""
    return None, reason


def generate_drafts(body: dict) -> dict:
    """Validate the request, then draft questions. Raises ``AIBusy`` when nothing was produced."""
    spec = _spec(body)
    context = _kb_excerpt(spec["syllabus"]) if spec["use_kb"] else ""
    warnings = []
    if spec["use_kb"] and not context:
        warnings.append("The knowledge base had no matching notes. Questions were written from the syllabus only.")
    logger.info(
        "class-test generate start mcq=%s coding=%s use_kb=%s difficulty=%s",
        spec["mcq_count"],
        spec["coding_count"],
        spec["use_kb"],
        spec["difficulty"],
    )
    questions: list[dict] = []
    flagged: list[dict] = []
    busy = False
    budget = {"n": 0}
    avoid = list(spec["avoid"])
    mcq_left = spec["mcq_count"]
    while mcq_left and not busy:
        count = min(MCQ_CHUNK, mcq_left)
        chunk_spec = {**spec, "avoid": avoid}
        try:
            made, reason = _chunk_mcq(chunk_spec, context, count, budget)
        except AIBusy:
            busy = True
            break
        except Exception as exc:
            logger.warning("class-test generate mcq chunk failed error_type=%s", type(exc).__name__)
            flagged.append({"type": "mcq", "prompt": spec["syllabus"][:120], "reason": "The model response could not be read"})
            break
        if not made:
            flagged.append({"type": "mcq", "prompt": spec["syllabus"][:120], "reason": reason or "Could not validate the MCQs"})
            break
        questions.extend(made)
        avoid.extend(question["prompt"][:300] for question in made)
        mcq_left -= len(made)
    coding_left = spec["coding_count"]
    while coding_left and not busy:
        chunk_spec = {**spec, "avoid": avoid}
        try:
            made, reason = _chunk_coding(chunk_spec, context, budget)
        except AIBusy:
            busy = True
            break
        except Exception as exc:
            logger.warning("class-test generate coding chunk failed error_type=%s", type(exc).__name__)
            flagged.append({"type": "coding", "prompt": spec["syllabus"][:120], "reason": "The model response could not be read"})
            coding_left -= 1
            continue
        coding_left -= 1
        if made is None:
            flagged.append({"type": "coding", "prompt": spec["syllabus"][:120], "reason": reason or "Reference solution failed"})
            continue
        questions.append(made)
        avoid.append(made["prompt"][:300])
    produced = len(questions)
    if busy and produced == 0:
        logger.info("class-test generate busy before any question")
        raise AIBusy()
    partial = busy or produced < (spec["mcq_count"] + spec["coding_count"])
    logger.info(
        "class-test generate done questions=%s flagged=%s partial=%s busy=%s calls=%s",
        produced,
        len(flagged),
        partial,
        busy,
        budget["n"],
    )
    return {
        "questions": questions,
        "flagged": flagged,
        "warnings": warnings,
        "partial": partial,
        "busy": busy,
    }
