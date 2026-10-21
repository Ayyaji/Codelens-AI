"""Create the MongoDB indexes CodeLens expects.

    python -m rag_core.init_db

The API creates the same indexes on startup. This command is for a manual
check, and for the database-design notes in the report.
"""

import asyncio

from rag_core.config import mongo_db_name, mongo_uri as configured_uri
from rag_core.mongo import close_mongo, get_db, ping


async def init_database() -> None:
    await ping()
    db = await get_db()
    print(f"MongoDB ready: {mongo_db_name()} at {configured_uri().split('@')[-1]}")
    names = sorted(await db.list_collection_names())
    print("Collections:")
    for name in names:
        info = await db[name].index_information()
        indexes = ", ".join(sorted(info))
        print(f"  {name}: {indexes}")


def main() -> None:
    async def _run() -> None:
        try:
            await init_database()
        finally:
            await close_mongo()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
