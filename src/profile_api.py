from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import List

app = FastAPI()

DB_PATH = "student_profiles.db"

# Models
class StudentCreate(BaseModel):
    student_id: str
    name: str
    learning_style: str

class WeakAreaCreate(BaseModel):
    student_id: str        # ← moved in from query param
    area: str
    count: int = 1

class ErrorLogCreate(BaseModel):
    student_id: str        # ← moved in from query param
    error_type: str
    error_message: str

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Endpoints

@app.post("/student-profile")
def create_student(profile: StudentCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO students (student_id, name, learning_style)
        VALUES (?, ?, ?)
        """, (profile.student_id, profile.name, profile.learning_style))
        conn.commit()
        return {"status": "created", "student_id": profile.student_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Student already exists")
    finally:
        conn.close()

@app.get("/student-profile/{student_id}")
def get_student(student_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found")
    cursor.execute("SELECT area, count FROM weak_areas WHERE student_id = ?", (student_id,))
    weak_areas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {
        "student_id": student_id,
        "name": student["name"],
        "learning_style": student["learning_style"],
        "weak_areas": weak_areas
    }

@app.post("/weak-areas")
def add_weak_area(data: WeakAreaCreate):          # ← no more query param
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO weak_areas (student_id, area, count)
        VALUES (?, ?, ?)
        """, (data.student_id, data.area, data.count))
        conn.commit()
        return {"status": "added", "area": data.area}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.get("/weak-areas/{student_id}")
def get_weak_areas(student_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT area, count FROM weak_areas WHERE student_id = ?", (student_id,))
    weak_areas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"student_id": student_id, "weak_areas": weak_areas}

@app.post("/error-log")
def log_error(data: ErrorLogCreate):              # ← no more query param
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO error_history (student_id, error_type, error_message)
        VALUES (?, ?, ?)
        """, (data.student_id, data.error_type, data.error_message))
        conn.commit()
        return {"status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

class ProfileUpdate(BaseModel):
    weak_area: str
    error_type: str
    error_message: str
@app.post("/update-profile/{student_id}")
def update_profile(student_id: str, data: ProfileUpdate):
    """Unified endpoint — update weak area + log error in one call."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Update weak area count or insert
        cursor.execute("""
            INSERT INTO weak_areas (student_id, area, count)
            VALUES (?, ?, 1)
            ON CONFLICT DO UPDATE SET count = count + 1
        """, (student_id, data.weak_area))

        # Log error
        cursor.execute("""
            INSERT INTO error_history (student_id, error_type, error_message)
            VALUES (?, ?, ?)
        """, (student_id, data.error_type, data.error_message))

        conn.commit()
        return {"status": "updated", "student_id": student_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)