"""Paths and environment shared by the API, agents, and scripts."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = ROOT / "knowledge_base" / "python_error.txt"

_env_loaded = False


def load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def get_db_path() -> str:
    """Legacy SQLite file, used only by the migration script."""
    load_env()
    return os.getenv("CODELENS_DB", str(ROOT / "codelens.db"))


def get_kb_dir() -> str:
    load_env()
    return os.getenv("CODELENS_KB", str(ROOT / "codelens_kb"))


def mongo_uri() -> str:
    load_env()
    return os.getenv("MONGODB_URI", "mongodb://localhost:27017")


def mongo_db_name() -> str:
    load_env()
    return os.getenv("MONGODB_DB", "codelens")


# Long enough for HS256. Replace it before any shared deployment.
DEFAULT_JWT_SECRET = "change-me-to-a-long-random-string"


def jwt_secret() -> str:
    load_env()
    return os.getenv("JWT_SECRET") or DEFAULT_JWT_SECRET


# The Vite dev server (`npm run dev`) and `npm run preview`. Listed so a laptop
# pointed at a deployed API still works. These origins cannot read a browser
# token stored on the public site.
VITE_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def cors_origin_regex() -> str | None:
    """Optional pattern matched against the whole browser ``Origin`` header.

    The simple deploy sets this so every ``https://*.vercel.app`` site can
    call the API. Empty means there is no pattern. The process reads it once,
    at startup.
    """
    load_env()
    raw = os.getenv("CORS_ORIGIN_REGEX", "").strip()
    return raw or None


def cors_origins() -> list[str]:
    """Browser origins allowed to call the API.

    ``CORS_ORIGINS`` is a comma-separated list, set at process start. The
    three-server deploy does not need it (the browser talks only to Nginx).
    Set it to the CloudFront origin when the static site is hosted on S3,
    or to a custom frontend origin on the simple deploy. ``CORS_ORIGIN_REGEX``
    covers ``https://*.vercel.app`` on that deploy. When both are empty the
    API keeps the local default and allows any origin. A trailing slash is
    ignored. A regex does not open every origin: an empty list then allows
    only the Vite dev servers plus whatever the regex matches.
    """
    load_env()
    raw = os.getenv("CORS_ORIGINS", "").strip()
    locked = bool(os.getenv("CORS_ORIGIN_REGEX", "").strip())
    if (not raw or raw == "*") and not locked:
        return ["*"]
    origins: list[str] = []
    seen: set[str] = set()
    listed = [] if not raw or raw == "*" else raw.split(",")
    for item in [*listed, *VITE_DEV_ORIGINS]:
        origin = item.strip().rstrip("/")
        if not origin or origin == "*" or origin in seen:
            continue
        seen.add(origin)
        origins.append(origin)
    if not origins and not locked:
        return ["*"]
    return origins
