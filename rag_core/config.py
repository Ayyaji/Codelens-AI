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
