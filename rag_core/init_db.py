import sqlite3

DB_PATH = "./codelens.db"

def init_database():
    """
    Initialize complete CodeLens database with all tables.
    Creates tables if they don't exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create sessions table
    print("Creating sessions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            query TEXT NOT NULL,
            agent_used TEXT NOT NULL,
            response_time REAL,
            timestamp TEXT NOT NULL,
            error_type TEXT,
            topic TEXT
        )
    """)
    print("✅ sessions table ready")
    
    # 2. Create kb_pending table
    print("Creating kb_pending table...")
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
    print("✅ kb_pending table ready")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database initialization complete")
    print(f"Database location: {DB_PATH}")

if __name__ == "__main__":
    print("Initializing CodeLens AI database...")
    print("="*60)
    init_database()
    
    # Show all tables
    print("\nVerifying tables:")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  ✓ {table[0]}")
    conn.close()