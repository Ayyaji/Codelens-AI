"""Paths shared by the API, agents, and scripts."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = ROOT / "knowledge_base" / "python_error.txt"


def get_db_path() -> str:
    return os.getenv("CODELENS_DB", str(ROOT / "codelens.db"))


def get_kb_dir() -> str:
    return os.getenv("CODELENS_KB", str(ROOT / "codelens_kb"))
