import sqlite3

def init_db():
    """Create student profile database."""
    conn = sqlite3.connect("student_profiles.db")
    cursor = conn.cursor()
    
    # Student profiles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT,
        learning_style TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Weak areas table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weak_areas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        area TEXT,
        count INTEGER DEFAULT 1,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    # Error history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS error_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        error_type TEXT,
        error_message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized!")