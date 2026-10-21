"""Parse a job description into skills and a preparation roadmap.

The analysis is cached in MongoDB by a hash of the text, so the same JD is
not sent to the model twice. PDF and plain text are both accepted. The model
is only called on a cache miss, and only for the structured parse.
"""

import logging

from rag_core.store import find_analysis, get_jd, insert_jd, save_analysis
from rag_core.timing import log_latency
from rag_core.util import content_hash

logger = logging.getLogger("codelens.agents")

MAX_STORED_CHARS = 200_000
MAX_PROMPT_CHARS = 80_000
LEVELS = {"beginner", "intermediate", "advanced"}
LEVEL_ALIASES = {
    "junior": "beginner",
    "entry": "beginner",
    "basic": "beginner",
    "mid": "intermediate",
    "medium": "intermediate",
    "senior": "advanced",
    "expert": "advanced",
}


def extract_text(raw: bytes, filename: str) -> str:
    """Turn an uploaded PDF or text file into JD text. No model involved."""
    name = (filename or "").lower()
    if name.endswith(".pdf") or raw.startswith(b"%PDF"):
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        text = raw.decode("utf-8", errors="replace")
    return text.replace("\x00", "").strip()


async def store_jd(text: str, filename: str, user_id: str) -> str:
    """Persist the JD for this student and return its id. Analysis happens later."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Job description is empty")
    if len(cleaned) > MAX_STORED_CHARS:
        raise ValueError("Job description is too long")
    return await insert_jd(user_id, cleaned, filename, content_hash(cleaned))


async def _load_jd(jd_id: str, user_id: str):
    row = await get_jd(jd_id, user_id)
    if row is None:
        raise LookupError(jd_id)
    return row


def _level(value: str) -> str:
    key = (value or "").strip().lower()
    key = LEVEL_ALIASES.get(key, key)
    return key if key in LEVELS else "intermediate"


def _roadmap(items) -> list[dict]:
    if not isinstance(items, list):
        return []
    steps = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            steps.append({"order": index, "skill": "", "goal": item.strip(), "practice": item.strip()})
            continue
        if not isinstance(item, dict):
            continue
        practice = item.get("practice") or item.get("activity") or item.get("actions") or ""
        if isinstance(practice, list):
            practice = "; ".join(str(part) for part in practice)
        goal = item.get("goal") or item.get("title") or item.get("explanation") or ""
        steps.append(
            {
                "order": int(item.get("order") or index),
                "skill": str(item.get("skill") or item.get("title") or "").strip(),
                "goal": str(goal).strip(),
                "practice": str(practice).strip(),
            }
        )
    return steps


def _normalize(data: dict) -> dict:
    if "skills" not in data:
        for key in ("analysis", "result", "data"):
            nested = data.get(key)
            if isinstance(nested, dict) and "skills" in nested:
                data = nested
                break
    skills = []
    for item in data.get("skills") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        explanation = str(item.get("explanation") or "").strip()
        if not name or not explanation:
            continue
        skills.append(
            {"name": name, "level": _level(str(item.get("level") or "")), "explanation": explanation}
        )
    roadmap = _roadmap(data.get("roadmap"))
    if not skills or not roadmap:
        raise RuntimeError("The job description could not be parsed into skills and a roadmap")
    return {"skills": skills, "roadmap": roadmap}


def _parse_with_model(text: str) -> dict:
    from rag_core.llm import complete_json

    prompt = f"""Parse this job description for a student preparing for interviews.
Return only JSON with this shape:
{{
  "skills": [{{"name": "short skill name", "level": "beginner|intermediate|advanced", "explanation": "what this requirement means in the role"}}],
  "roadmap": [{{"order": 1, "skill": "skill name", "goal": "what to be able to do", "practice": "one concrete practice task"}}]
}}
Use the skills you list. Order the roadmap from foundations to the work the posting emphasises.
Do not invent requirements that are not supported by the text.

Job description:
{text[:MAX_PROMPT_CHARS]}
"""
    return _normalize(complete_json("small", prompt))


async def analyse_jd(jd_id: str, user_id: str) -> dict:
    """Return skills and a roadmap, using the Mongo cache when the text matches."""
    with log_latency("jd_analyser") as info:
        row = await _load_jd(jd_id, user_id)
        if isinstance(row.get("analysis"), dict):
            info["cache"] = "hit"
            return row["analysis"]
        cached = await find_analysis(row["content_hash"])
        if cached:
            info["cache"] = "hit"
            await save_analysis(jd_id, cached)
            return cached

        info["cache"] = "miss"
        analysis = _parse_with_model(row["raw_text"])
        await save_analysis(jd_id, analysis)
        logger.info("cached jd analysis hash=%s", row["content_hash"][:12])
        return analysis
