"""Field checks for the teacher knowledge-base library.

Messages match the sentences the library page shows. Web proposals skip this
module: they are staged with whatever text the agent returned.
"""

KB_TYPES = {"concept", "qa", "college", "document"}
KB_SOURCES = {"teacher", "student", "ai", "web", "upload", "textbook"}
KB_DIFFICULTIES = {"easy", "medium", "hard"}
MAX_TITLE = 140
MAX_TOPIC = 60
MAX_TAG = 32
MAX_TAGS = 8
MAX_CONTENT = 20_000


class KBInputError(ValueError):
    """The teacher sent a note the library cannot store. The API maps this to 422."""


def clean_tags(value) -> list[str]:
    if value is None:
        raw: list = []
    elif isinstance(value, str):
        raw = value.split(",")
    elif isinstance(value, list):
        raw = value
    else:
        raise KBInputError("Tags must be a list")
    tags: list[str] = []
    for entry in raw:
        tag = " ".join(str(entry or "").split()).lower()
        if not tag or tag in tags:
            continue
        if len(tag) > MAX_TAG:
            raise KBInputError("Tags must be 32 characters or fewer")
        tags.append(tag)
        if len(tags) > MAX_TAGS:
            raise KBInputError("Use at most 8 tags")
    return tags


def _required(value, label: str, limit: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise KBInputError(f"{label} is required")
    if len(text) > limit:
        raise KBInputError(f"{label} must be {limit} characters or fewer")
    return text


def _difficulty(value) -> str | None:
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text not in KB_DIFFICULTIES:
        raise KBInputError("Difficulty must be easy, medium, or hard")
    return text


def _content(value) -> str:
    text = str(value or "").strip()
    if not text:
        raise KBInputError("Content is required")
    if len(text) > MAX_CONTENT:
        raise KBInputError("Content is too long")
    return text


def validate_create(body: dict) -> dict:
    """Full note from POST /teacher/kb. ``approve`` defaults to true."""
    source = body.get("source") or "teacher"
    if source not in KB_SOURCES:
        raise KBInputError("Unknown source")
    note_type = body.get("type") or "concept"
    if note_type not in KB_TYPES:
        raise KBInputError("Unknown note type")
    title = _required(body.get("title"), "Title", MAX_TITLE)
    approve = body.get("approve")
    return {
        "title": title,
        "content": _content(body.get("content")),
        "topic": _required(body.get("topic"), "Topic", MAX_TOPIC),
        "tags": clean_tags(body.get("tags") or []),
        "difficulty": _difficulty(body.get("difficulty")),
        "source": source,
        "type": note_type,
        "query": title,
        "approve": True if approve is None else bool(approve),
    }


def validate_patch(body: dict) -> dict:
    """Fields present on PUT. Absent keys are left alone. ``approve`` is not a field."""
    updates: dict = {}
    if "title" in body:
        title = _required(body.get("title"), "Title", MAX_TITLE)
        updates["title"] = title
        updates["query"] = title
    if "content" in body:
        updates["content"] = _content(body.get("content"))
    if "topic" in body:
        updates["topic"] = _required(body.get("topic"), "Topic", MAX_TOPIC)
    if "tags" in body:
        updates["tags"] = clean_tags(body.get("tags"))
    if "difficulty" in body:
        updates["difficulty"] = _difficulty(body.get("difficulty"))
    if "type" in body:
        note_type = str(body.get("type") or "")
        if note_type not in KB_TYPES:
            raise KBInputError("Unknown note type")
        updates["type"] = note_type
    if "source" in body:
        source = str(body.get("source") or "")
        if source not in KB_SOURCES:
            raise KBInputError("Unknown source")
        updates["source"] = source
    return updates
