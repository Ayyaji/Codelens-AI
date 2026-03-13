import sqlite3
from datetime import datetime

DB_PATH = "./codelens.db"

def init_db():
    """Create kb_pending table if not exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

def stage_for_approval(query: str, content: str, source: str = None):
    """Stage new content for teacher approval"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO kb_pending (query, content, source, timestamp, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (query, content, source, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"✅ Staged for teacher approval: {query[:50]}...")

def get_pending_items():
    """Get all pending KB items — used by M3 teacher dashboard"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kb_pending WHERE status='pending'")
    items = cursor.fetchall()
    conn.close()
    return items

def approve_item(item_id: int):
    """Teacher approves — content enters ChromaDB"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the content
    cursor.execute("SELECT query, content FROM kb_pending WHERE id=?", (item_id,))
    item = cursor.fetchone()
    
    if not item:
        conn.close()
        return False
    
    query, content = item
    
    # Add to ChromaDB
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain.schema import Document
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(
        persist_directory="./codelens_kb",
        embedding_function=embeddings
    )
    
    doc = Document(page_content=content, metadata={"source": "web", "query": query})
    vectorstore.add_documents([doc])
    
    # Update status
    cursor.execute("UPDATE kb_pending SET status='approved' WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    
    print(f"✅ Item {item_id} approved and added to ChromaDB")
    return True

def reject_item(item_id: int):
    """Teacher rejects — content deleted"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE kb_pending SET status='rejected' WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    print(f"❌ Item {item_id} rejected")


# Test
if __name__ == "__main__":
    init_db()
    stage_for_approval(
        query="What is Docker?",
        content="Docker is a containerization platform that packages applications with their dependencies.",
        source="https://docker.com"
    )
    
    items = get_pending_items()
    print(f"\nPending items: {len(items)}")
    for item in items:
        print(f"ID: {item[0]} | Query: {item[2][:40]} | Status: {item[5]}")