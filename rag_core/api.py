import time
from fastapi import FastAPI
from pydantic import BaseModel
from rag_core.pipeline import run_pipeline
from rag_core.kb_update import get_pending_items, approve_item, reject_item

app = FastAPI(title="CodeLens AI API")

class QueryRequest(BaseModel):
    student_id: str
    query: str

class QueryResponse(BaseModel):
    student_id: str
    query: str
    agent_used: str
    answer: str
    directive: str

@app.get("/")
def root():
    return {"message": "CodeLens AI is running"}

@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    result = run_pipeline(request.query, student_id=request.student_id)

    answer = result["answer"]
    if isinstance(answer, dict):
        answer = answer.get("answer", "No answer found")

    return QueryResponse(
        student_id=request.student_id,
        query=result["query"],
        agent_used=result["agent_used"],
        answer=answer,
        directive=result["directive"]
    )

@app.get("/pending-kb")
def pending_kb():
    items = get_pending_items()
    return {
        "count": len(items),
        "items": [{"id": i[0], "query": i[1], "content": i[2], "source": i[3], "timestamp": i[4], "status": i[5]} for i in items]
    }

@app.post("/approve-kb/{item_id}")
def approve_kb(item_id: int):
    success = approve_item(item_id)
    return {"message": f"Item {item_id} {'approved and added to KB' if success else 'not found'}"}

@app.post("/reject-kb/{item_id}")
def reject_kb(item_id: int):
    reject_item(item_id)
    return {"message": f"Item {item_id} rejected"}

@app.get("/sessions")
def get_sessions():
    import sqlite3, os
    db = os.path.join(os.path.dirname(__file__), "codelens.db")
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return {"count": len(rows), "sessions": [{"id": r[0], "student_id": r[1], "query": r[2], "agent_used": r[3], "response_time": r[4], "timestamp": r[5]} for r in rows]}
