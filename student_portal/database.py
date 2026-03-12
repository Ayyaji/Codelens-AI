import sqlite3
from datetime import datetime
def get_connection():
    conn = sqlite3.connect("codelens.db")
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            error_text TEXT NOT NULL,
            answer TEXT NOT NULL,
            agent_used TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS behaviour (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            avg_wpm REAL NOT NULL,
            backspace_count INTEGER NOT NULL,
            duration INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()
def add_student(username, password, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO students (username, password, name)
        VALUES (?, ?, ?)
    """, (username, password, name))
    conn.commit()
    conn.close()

def get_student(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM students 
        WHERE username = ? AND password = ?
    """, (username, password))
    student = cursor.fetchone()
    conn.close()
    return student

def log_session(student_id, error_text, answer, agent_used, duration_seconds):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions 
        (student_id, error_text, answer, agent_used, timestamp, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, error_text, answer, agent_used, 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration_seconds))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def log_behaviour(student_id, session_id, avg_wpm, backspace_count, duration):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO behaviour 
        (student_id, session_id, avg_wpm, backspace_count, duration)
        VALUES (?, ?, ?, ?, ?)
    """, (student_id, session_id, avg_wpm, backspace_count, duration))
    conn.commit()
    conn.close()

def get_student_sessions(student_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM sessions 
        WHERE student_id = ? 
        ORDER BY timestamp DESC
    """, (student_id,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions
if __name__ == "__main__":
    init_db()
    print("✅ Database created successfully")

    add_student("arjun", "1234", "Arjun K")
    print("✅ Student added")

    student = get_student("arjun", "1234")
    print("✅ Login test:", student["name"])

    session_id = log_session(1, "NameError: x not defined", "You forgot to declare x", "Debug Agent", 12)
    print("✅ Session logged, ID:", session_id)

    log_behaviour(1, session_id, 45.5, 3, 12)
    print("✅ Behaviour logged")

    sessions = get_student_sessions(1)
    print("✅ Sessions found:", len(sessions))