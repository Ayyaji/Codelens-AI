"""Stage web results for a teacher before they enter the knowledge base."""

from datetime import datetime

from rag_core.config import get_kb_dir
from rag_core.db import connection, init_db


def stage_for_approval(query: str, content: str, source: str = None):
    """Stage new content for teacher approval."""
    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO kb_pending (query, content, source, timestamp, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (query, content, source, datetime.now().isoformat()),
        )
    print(f"Staged for teacher approval: {query[:50]}...")


def get_pending_items():
    """Return pending knowledge-base items for the teacher dashboard."""
    init_db()
    with connection() as conn:
        items = [
            tuple(row)
            for row in conn.execute(
                "SELECT * FROM kb_pending WHERE status='pending'"
            ).fetchall()
        ]
    return items


def approve_item(item_id: int):
    """Teacher approves an item and it is added to Chroma."""
    init_db()
    with connection() as conn:
        item = conn.execute(
            "SELECT query, content FROM kb_pending WHERE id=?",
            (item_id,),
        ).fetchone()
        if not item:
            return False
        query, content = item[0], item[1]
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(persist_directory=get_kb_dir(), embedding_function=embeddings)
        vectorstore.add_documents(
            [Document(page_content=content, metadata={"source": "web", "query": query})]
        )
        conn.execute("UPDATE kb_pending SET status='approved' WHERE id=?", (item_id,))
    print(f"Item {item_id} approved and added to the knowledge base")
    return True


def reject_item(item_id: int):
    """Teacher rejects an item. It stays in SQLite with status rejected."""
    init_db()
    with connection() as conn:
        conn.execute("UPDATE kb_pending SET status='rejected' WHERE id=?", (item_id,))
    print(f"Item {item_id} rejected")
