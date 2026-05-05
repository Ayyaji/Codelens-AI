import json
import sqlite3
import chromadb
from chromadb.utils import embedding_functions

DB_PATH = "student_profiles.db"
PROFILES_PATH = "evaluation/student_profiles.json"
CHROMA_PATH = "evaluation/student_chromadb"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_profiles():
    with open(PROFILES_PATH, "r") as f:
        return json.load(f)

def get_weak_areas(conn, student_id):
    cursor = conn.cursor()
    cursor.execute("SELECT area, count FROM weak_areas WHERE student_id = ?", (student_id,))
    return cursor.fetchall()

def get_error_history(conn, student_id):
    cursor = conn.cursor()
    cursor.execute("SELECT error_type, error_message FROM error_history WHERE student_id = ?", (student_id,))
    return cursor.fetchall()

def build_chroma_for_student(student, weak_areas, error_history, collection):
    docs = []
    ids = []
    metadatas = []

    # Add weak areas as documents
    for i, row in enumerate(weak_areas):
        doc = f"Student struggles with: {row['area']} (occurred {row['count']} times)"
        docs.append(doc)
        ids.append(f"weak_{i}")
        metadatas.append({"type": "weak_area", "area": row["area"]})

    # Add error history as documents
    for i, row in enumerate(error_history):
        doc = f"Error encountered: {row['error_type']} — {row['error_message']}"
        docs.append(doc)
        ids.append(f"error_{i}")
        metadatas.append({"type": "error_log", "error_type": row["error_type"]})

    # Add profile summary
    summary = f"Student {student['name']} has learning style: {student.get('learning_style', 'unknown')}"
    docs.append(summary)
    ids.append("profile_summary")
    metadatas.append({"type": "profile"})

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metadatas)
        print(f"  Added {len(docs)} documents")
    else:
        print(f"  No data found — adding placeholder")
        collection.add(
            documents=[f"Student {student['name']} has no error history yet."],
            ids=["placeholder"],
            metadatas=[{"type": "placeholder"}]
        )

def main():
    profiles = load_profiles()
    conn = get_db()

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()

    for student in profiles:
        student_id = student["student_id"]
        name = student["name"]
        print(f"\nBuilding ChromaDB for {name} ({student_id})...")

        # Delete existing collection if rebuilding
        try:
            chroma_client.delete_collection(name=f"student_{student_id}")
        except:
            pass

        collection = chroma_client.create_collection(
            name=f"student_{student_id}",
            embedding_function=ef
        )

        weak_areas = get_weak_areas(conn, student_id)
        error_history = get_error_history(conn, student_id)
        build_chroma_for_student(student, weak_areas, error_history, collection)

    conn.close()
    print("\nDone! Per-student ChromaDB built at evaluation/student_chromadb/")

if __name__ == "__main__":
    main()