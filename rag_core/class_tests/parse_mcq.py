"""Turn a JSON array or a pasted quiz into MCQ question objects.

Nothing is stored. The teacher reviews the questions and saves them on a test.
"""

import json
import re

from rag_core.class_tests.errors import ClassTestError

_MAX_TEXT = 100_000
_MAX_QUESTIONS = 50
_OPTION = re.compile(r"^\s*([A-Da-d])[\)\.\:]\s*(.+?)\s*$")
_QUESTION = re.compile(r"^\s*(?:Q(?:uestion)?\s*[:.)]|(\d+)\s*[.)])\s*(.+?)\s*$", re.IGNORECASE)
_ANSWER = re.compile(r"^\s*Answer\s*[:.)]\s*(.+?)\s*$", re.IGNORECASE)
_FIELD = re.compile(r"^\s*(Explanation|Skill|Topic)\s*[:.)]\s*(.*)\s*$", re.IGNORECASE)


def _new_id(index: int) -> str:
    return f"mcq_paste_{index}"


def _resolve_index(options: list[str], raw) -> int:
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        raise ClassTestError(422, "Each MCQ needs an answer")
    if isinstance(raw, bool):
        raise ClassTestError(422, "An MCQ answer must be an index, a letter, or the option text")
    if isinstance(raw, int):
        if 0 <= raw < len(options):
            return raw
        raise ClassTestError(422, "correct_index is outside the options")
    text = str(raw).strip()
    for index, option in enumerate(options):
        if text.lower() == option.strip().lower():
            return index
    if len(text) == 1 and text.upper() in "ABCD":
        index = ord(text.upper()) - ord("A")
        if index < len(options):
            return index
    if text.isdigit():
        index = int(text)
        if 0 <= index < len(options):
            return index
    raise ClassTestError(422, f"Could not match answer {text!r} to an option")


def _clean_options(raw) -> list[str]:
    if not isinstance(raw, list) or not 2 <= len(raw) <= 6:
        raise ClassTestError(422, "Each MCQ needs 2 to 6 options")
    options = []
    for option in raw:
        text = str(option).strip()
        if not text:
            raise ClassTestError(422, "MCQ options cannot be blank")
        if len(text) > 300:
            raise ClassTestError(422, "An option is longer than 300 characters")
        options.append(text)
    return options


def question_from_mapping(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ClassTestError(422, "Each question must be an object")
    prompt = str(raw.get("prompt") or raw.get("question") or "").strip()
    if not prompt:
        raise ClassTestError(422, "Each MCQ needs a prompt")
    if len(prompt) > 2000:
        raise ClassTestError(422, "A prompt is longer than 2000 characters")
    options = _clean_options(raw.get("options"))
    answer = raw.get("correct_index", raw.get("answer", raw.get("correct")))
    correct_index = _resolve_index(options, answer)
    skill = str(raw.get("skill") or raw.get("topic") or "general").strip() or "general"
    topic = str(raw.get("topic") or skill).strip() or skill
    explanation = str(raw.get("explanation") or "").strip()
    qid = str(raw.get("id") or "").strip() or _new_id(index)
    return {
        "id": qid[:40],
        "type": "mcq",
        "topic": topic[:60],
        "skill": skill[:60],
        "prompt": prompt,
        "options": options,
        "correct_index": correct_index,
        "explanation": explanation[:2000],
    }


def _parse_json(text: str) -> list[dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ClassTestError(422, "That text is not valid JSON") from exc
    if isinstance(data, dict):
        data = data.get("questions")
    if not isinstance(data, list):
        raise ClassTestError(422, "Paste a JSON array of questions, or an object with a questions array")
    if len(data) > _MAX_QUESTIONS:
        raise ClassTestError(422, f"Paste at most {_MAX_QUESTIONS} questions at once")
    return [question_from_mapping(item, index) for index, item in enumerate(data, start=1)]


def _joined(value, default: str) -> str:
    """Skill and topic are stored as line lists while a paste is being read."""
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    text = str(value or "").strip()
    return text or default


def _flush(block: dict, index: int, out: list[dict]) -> None:
    if not block:
        return
    letters = [letter for letter in "ABCD" if letter in block["options"]]
    if letters != list("ABCD"[: len(letters)]):
        raise ClassTestError(422, f"Question {index} options must start at A without skipping a letter")
    options = [block["options"][letter] for letter in letters]
    if len(options) < 2:
        raise ClassTestError(422, f"Question {index} needs at least two options")
    skill = _joined(block.get("skill"), "general")
    raw = {
        "prompt": " ".join(block["prompt"]).strip(),
        "options": options,
        "answer": block.get("answer"),
        "explanation": " ".join(block.get("explanation") or []).strip(),
        "skill": skill,
        "topic": _joined(block.get("topic"), skill),
    }
    out.append(question_from_mapping(raw, index))


def _parse_text(text: str) -> list[dict]:
    out: list[dict] = []
    block: dict | None = None
    mode = ""
    index = 0
    for line in text.splitlines():
        if not line.strip():
            if block and block.get("answer"):
                index += 1
                _flush(block, index, out)
                block = None
                mode = ""
            continue
        question = _QUESTION.match(line)
        if question:
            if block and block.get("prompt"):
                index += 1
                _flush(block, index, out)
            block = {"prompt": [question.group(2).strip()], "options": {}}
            mode = "prompt"
            continue
        if block is None:
            continue
        option = _OPTION.match(line)
        if option:
            block["options"][option.group(1).upper()] = option.group(2).strip()
            mode = ""
            continue
        answer = _ANSWER.match(line)
        if answer:
            block["answer"] = answer.group(1).strip()
            mode = ""
            continue
        field = _FIELD.match(line)
        if field:
            name = field.group(1).lower()
            block[name] = [field.group(2).strip()]
            mode = name
            continue
        if mode in {"explanation", "skill", "topic"}:
            block.setdefault(mode, []).append(line.strip())
        elif mode == "prompt" or not block["options"]:
            block["prompt"].append(line.strip())
    if block and block.get("prompt"):
        index += 1
        _flush(block, index, out)
    if len(out) > _MAX_QUESTIONS:
        raise ClassTestError(422, f"Paste at most {_MAX_QUESTIONS} questions at once")
    return out


def parse_mcq_import(*, text: str = "", questions: list | None = None) -> list[dict]:
    """Normalize pasted MCQs. JSON is detected when ``text`` starts with ``[`` or ``{``."""
    if questions:
        if len(questions) > _MAX_QUESTIONS:
            raise ClassTestError(422, f"Paste at most {_MAX_QUESTIONS} questions at once")
        return [question_from_mapping(item, index) for index, item in enumerate(questions, start=1)]
    body = (text or "").strip()
    if not body:
        raise ClassTestError(422, "Paste some questions")
    if len(body) > _MAX_TEXT:
        raise ClassTestError(422, "That paste is too long")
    if body[0] in "[{":
        parsed = _parse_json(body)
    else:
        parsed = _parse_text(body)
    if not parsed:
        raise ClassTestError(422, "No questions found. Paste a JSON array or questions marked with Q:")
    return parsed
