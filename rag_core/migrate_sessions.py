"""Old entry point from when sessions lived in SQLite.

``python -m rag_core.init_db`` creates the MongoDB indexes.
``python -m rag_core.migrate_sqlite`` copies an existing codelens.db.
"""


def migrate_sessions_table() -> None:
    print("SQLite session columns are no longer migrated in place.")
    print("Run: python -m rag_core.migrate_sqlite")


if __name__ == "__main__":
    migrate_sessions_table()
