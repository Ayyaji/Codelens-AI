"""Small helpers that do not need a model."""

import hashlib
import json


def content_hash(text: str) -> str:
    normalized = " ".join(text.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def skills_cache_key(skills: list[dict]) -> str:
    canonical = [
        {
            "name": str(skill.get("name", "")).strip().casefold(),
            "level": str(skill.get("level", "")).strip().casefold(),
        }
        for skill in skills
    ]
    canonical.sort(key=lambda item: (item["name"], item["level"]))
    return content_hash(json.dumps(canonical, sort_keys=True))
