import sqlite3
from datetime import datetime
from rag_core.judgment import extract_error_type, extract_topic

DB_PATH = "./codelens.db"

def log_session(student_id: str, query: str, agent_used: str, response_time: float):
    """
    Log a student session with automatic error_type and topic extraction.
    """
    # Extract metadata from query
    error_type = extract_error_type(query)
    topic = extract_topic(query)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sessions (student_id, query, agent_used, response_time, timestamp, error_type, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id,
        query,
        agent_used,
        response_time,
        datetime.now().isoformat(),
        error_type,
        topic
    ))
    
    conn.commit()
    conn.close()

# Test
if __name__ == "__main__":
    print("Testing session logging with judgment fields...")
    
    test_sessions = [
        ("student_1", "I'm getting NameError: name 'x' is not defined", "debug", 2.5),
        ("student_1", "Still getting NameError", "debug", 3.1),
        ("student_2", "What is recursion?", "concept", 2.0),
    ]
    
    for student_id, query, agent, time in test_sessions:
        log_session(student_id, query, agent, time)
        print(f"✅ Logged: {query[:40]}...")
    
    # Verify
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, query, error_type, topic FROM sessions ORDER BY timestamp DESC LIMIT 3")
    rows = cursor.fetchall()
    conn.close()
    
    print("\nLast 3 sessions:")
    for row in rows:
        print(f"  {row[0]}: {row[1][:30]}... | error={row[2]}, topic={row[3]}")