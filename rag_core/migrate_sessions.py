"""Add judgment columns to a sessions table created before those fields existed.

`python -m rag_core.init_db` already does this. This script remains so the
older command still works.
"""

from rag_core.db import init_db


def migrate_sessions_table():
    init_db()
    print("Sessions table has error_type and topic")


if __name__ == "__main__":
    migrate_sessions_table()
