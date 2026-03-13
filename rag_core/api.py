from fastapi import FastAPI
from pydantic import BaseModel
from rag_core.pipeline import run_pipeline

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