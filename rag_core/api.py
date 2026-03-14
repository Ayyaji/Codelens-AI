from fastapi import FastAPI
from pydantic import BaseModel
from rag_core.pipeline import run_pipeline
from rag_core.kb_update import (
    stage_for_approval,
    get_pending_items,
    approve_item,
    reject_item
)

app = FastAPI(title="CodeLens AI API")

class QueryRequest(BaseModel):
    student_id: str
    query: str

class QueryResponse(BaseModel):
    student_id: str
    query: str
    agent_used: str
    answer: str

@app.get("/")
def root():
    return {"message": "CodeLens AI is running"}

@app.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    result = run_pipeline(request.query)
    
    answer = result["answer"]
    if isinstance(answer, dict):
        answer = answer.get("answer", "No answer found")
    
    return QueryResponse(
        student_id=request.student_id,
        query=result["query"],
        agent_used=result["agent_used"],
        answer=answer
    )

@app.get("/pending-kb")
def pending_kb():
    items = get_pending_items()
    return {
        "count": len(items),
        "items": [
            {
                "id": item[0],
                "query": item[1],
                "content": item[2],
                "source": item[3],
                "timestamp": item[4],
                "status": item[5]
            }
            for item in items
        ]
    }

@app.post("/approve-kb/{item_id}")
def approve_kb(item_id: int):
    success = approve_item(item_id)
    if success:
        return {"message": f"Item {item_id} approved and added to KB"}
    return {"message": f"Item {item_id} not found"}

@app.post("/reject-kb/{item_id}")
def reject_kb(item_id: int):
    reject_item(item_id)
    return {"message": f"Item {item_id} rejected"}