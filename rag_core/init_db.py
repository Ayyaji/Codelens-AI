"""Create the CodeLens SQLite database."""

import sqlite3

from rag_core.config import get_db_path
from rag_core.db import init_db


def init_database():
    """Create every table the judgment layer and the JD modules need."""
    init_db()
    print(f"Database ready at {get_db_path()}")


if __name__ == "__main__":
    print("Initializing CodeLens AI database")
    init_database()
    conn = sqlite3.connect(get_db_path())
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    conn.close()
    print("Tables:")
    for (name,) in tables:
        print(f"  {name}")
