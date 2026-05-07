import sqlite3

DB_PATH = "./codelens.db"

def migrate_sessions_table():
    """
    Add fields needed for judgment layer:
    - error_type: extracted from query (e.g., "NameError", "IndexError")
    - topic: general topic (e.g., "recursion", "loops", "docker")
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns already exist
    columns = cursor.execute("PRAGMA table_info(sessions)").fetchall()
    column_names = [col[1] for col in columns]
    
    if "error_type" not in column_names:
        print("Adding error_type column...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN error_type TEXT")
        print("✅ Added error_type")
    else:
        print("⚠️  error_type already exists")
    
    if "topic" not in column_names:
        print("Adding topic column...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN topic TEXT")
        print("✅ Added topic")
    else:
        print("⚠️  topic already exists")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration complete")

if __name__ == "__main__":
    print("Migrating sessions table for judgment layer...")
    print("="*60)
    migrate_sessions_table()
    
    # Show updated schema
    print("\nUpdated schema:")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    schema = cursor.execute("PRAGMA table_info(sessions)").fetchall()
    for col in schema:
        print(f"  {col[1]} ({col[2]})")
    conn.close()