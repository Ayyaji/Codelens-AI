"""Generate MCQ and coding questions from a JD's skills.

Questions are cached by a hash of the skill list. A later JD that asks for
the same skills reuses the stored test instead of calling the model again.
"""

import uuid

from rag_core.agents.jd_analyser import analyse_jd
from rag_core.schemas import QuestionPublic, StoredQuestion
from rag_core.store import questions_for_cache, questions_for_jd, save_test
from rag_core.timing import log_latency
from rag_core.util import skills_cache_key


def _align_answer(answer: str, options: list[str]) -> str:
    cleaned = answer.strip()
    for option in options:
        if option.strip().lower() == cleaned.lower():
            return option.strip()
    if len(cleaned) == 1 and cleaned.upper() in "ABCD":
        index = ord(cleaned.upper()) - ord("A")
        if 0 <= index < len(options):
            return options[index].strip()
    return cleaned


def normalize_questions(data: dict) -> list[dict]:
    """Keep well-formed questions and drop the answer key from nothing yet.

    Invalid items are skipped. Callers store the full records, including answers
    and every test case.
    """
    payload = data
    if "questions" not in payload:
        for key in ("test", "result", "data"):
            nested = payload.get(key)
            if isinstance(nested, dict) and "questions" in nested:
                payload = nested
                break
    stored: list[dict] = []
    for index, item in enumerate(payload.get("questions") or [], start=1):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or "").strip().lower()
        skill = str(item.get("skill") or "").strip()
        prompt = str(item.get("prompt") or item.get("question") or "").strip()
        if kind not in {"mcq", "coding"} or not skill or not prompt:
            continue
        question_id = str(item.get("id") or f"q{index}").strip() or f"q{index}"
        if kind == "mcq":
            options = [str(option).strip() for option in (item.get("options") or []) if str(option).strip()]
            answer = _align_answer(str(item.get("answer") or ""), options)
            if len(options) < 2 or not answer:
                continue
            record = StoredQuestion(
                id=question_id,
                type="mcq",
                skill=skill,
                prompt=prompt,
                options=options,
                answer=answer,
            )
        else:
            cases = []
            for case in item.get("test_cases") or []:
                if not isinstance(case, dict):
                    continue
                expected = case.get("expected")
                if expected is None:
                    continue
                stdin = case.get("input", case.get("stdin", ""))
                cases.append({"stdin": str(stdin), "expected": str(expected)})
            if not cases:
                continue
            record = StoredQuestion(
                id=question_id,
                type="coding",
                skill=skill,
                prompt=prompt,
                language=str(item.get("language") or "python"),
                starter_code=str(item.get("starter_code") or ""),
                test_cases=cases,
            )
        stored.append(record.model_dump(by_alias=True))
        if len(stored) >= 8:
            break
    if not stored:
        raise RuntimeError("The model did not return any usable questions")
    seen = set()
    for record in stored:
        if record["id"] in seen:
            record["id"] = uuid.uuid4().hex[:8]
        seen.add(record["id"])
    return stored


def to_public(questions: list[dict]) -> list[dict]:
    """Strip answer keys. Coding questions expose only the first sample case."""
    public = []
    for question in questions:
        if question["type"] == "mcq":
            item = QuestionPublic(
                id=question["id"],
                type="mcq",
                skill=question["skill"],
                prompt=question["prompt"],
                options=question.get("options") or [],
            )
        else:
            cases = question.get("test_cases") or []
            sample = cases[0] if cases else {}
            item = QuestionPublic(
                id=question["id"],
                type="coding",
                skill=question["skill"],
                prompt=question["prompt"],
                language=question.get("language") or "python",
                starter_code=question.get("starter_code") or "",
                sample_input=str(sample.get("input", sample.get("stdin", ""))),
                sample_output=str(sample.get("expected", "")),
            )
        public.append(item.model_dump(exclude_none=True))
    return public


async def load_questions(jd_id: str, user_id: str) -> list[dict] | None:
    from rag_core.store import get_jd

    if await get_jd(jd_id, user_id) is None:
        raise LookupError(jd_id)
    return await questions_for_jd(jd_id)


async def _save(jd_id: str, user_id: str, cache_key: str, questions: list[dict]) -> None:
    await save_test(jd_id, user_id, cache_key, questions)


async def _find_cached(cache_key: str) -> list[dict] | None:
    return await questions_for_cache(cache_key)


def _generate_with_model(skills: list[dict]) -> list[dict]:
    from rag_core.llm import complete_json

    skill_lines = "\n".join(f"- {item['name']} ({item['level']}): {item['explanation']}" for item in skills)
    prompt = f"""Write an interview practice test from these skills.
Return only JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "mcq",
      "skill": "skill name from the list",
      "prompt": "one question",
      "options": ["...", "...", "...", "..."],
      "answer": "the correct option text, exactly as written in options"
    }},
    {{
      "id": "c1",
      "type": "coding",
      "skill": "skill name from the list",
      "prompt": "program reads stdin and writes the answer to stdout",
      "language": "python",
      "starter_code": "",
      "test_cases": [{{"input": "stdin text", "expected": "stdout text"}}]
    }}
  ]
}}
Write 4 MCQs and 2 coding questions. Each coding question needs at least 2 stdin/stdout test cases.
The programs must be solvable with the Python standard library only. Do not ask for network or file access.

Skills:
{skill_lines}
"""
    return normalize_questions(complete_json("small", prompt))


async def generate_questions(jd_id: str, user_id: str) -> dict:
    """Return public questions for a JD, reusing a cached test when the skills match."""
    with log_latency("question_gen") as info:
        existing = await load_questions(jd_id, user_id)
        if existing is not None:
            info["cache"] = "hit"
            return {"jd_id": jd_id, "questions": to_public(existing)}

        analysis = await analyse_jd(jd_id, user_id)
        cache_key = skills_cache_key(analysis["skills"])
        reused = await _find_cached(cache_key)
        if reused is not None:
            info["cache"] = "reuse"
            await _save(jd_id, user_id, cache_key, reused)
            return {"jd_id": jd_id, "questions": to_public(reused)}

        info["cache"] = "miss"
        questions = _generate_with_model(analysis["skills"])
        await _save(jd_id, user_id, cache_key, questions)
        return {"jd_id": jd_id, "questions": to_public(questions)}
