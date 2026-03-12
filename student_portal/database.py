import sqlite3
import os
from datetime import datetime

def get_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "codelens.db")
    conn = sqlite3.connect(db_path)
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            subject TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
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

def add_teacher(username, password, name, subject):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO teachers (username, password, name, subject)
        VALUES (?, ?, ?, ?)
    """, (username, password, name, subject))
    conn.commit()
    conn.close()

def get_teacher(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM teachers 
        WHERE username = ? AND password = ?
    """, (username, password))
    teacher = cursor.fetchone()
    conn.close()
    return teacher

def get_all_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, st.name as student_name, s.error_text, 
               s.answer, s.agent_used, s.timestamp, 
               s.duration_seconds
        FROM sessions s
        JOIN students st ON s.student_id = st.id
        ORDER BY s.timestamp DESC
    """)
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def get_pending_kb():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM kb_pending 
        WHERE status = 'pending'
        ORDER BY timestamp DESC
    """)
    items = cursor.fetchall()
    conn.close()
    return items

def update_kb_status(kb_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE kb_pending SET status = ? WHERE id = ?
    """, (status, kb_id))
    conn.commit()
    conn.close()

def get_all_behaviour():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.id, st.name as student_name, b.avg_wpm, 
               b.backspace_count, b.duration, b.session_id
        FROM behaviour b
        JOIN students st ON b.student_id = st.id
        ORDER BY b.id DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return data