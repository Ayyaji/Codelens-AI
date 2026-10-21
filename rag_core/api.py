"""CodeLens AI HTTP API.

Two modules share this app:

1. JD understanding — upload a job description, then read the skills and roadmap.
2. Test and guide — generate a test, run code, submit answers, and receive a score,
   weak topics, and judgment-based guidance.

POST /ask stays the guidance chat. Debugging help is one of the agents it can route to.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from rag_core.agents.diagnoser import diagnose
from rag_core.agents.evaluator import evaluate_questions
from rag_core.agents.guide import build_guidance
from rag_core.agents.jd_analyser import analyse_jd, extract_text, store_jd
from rag_core.agents.question_gen import generate_questions, load_questions
from rag_core.agents.retrieval import warm_retrieval
from rag_core.db import connection, init_db
from rag_core.judgment import extract_error_type
from rag_core.kb_update import approve_item, get_pending_items, reject_item
from rag_core.llm import init_clients
from rag_core.pipeline import run_pipeline
from rag_core.sandbox.runner import run_code
from rag_core.schemas import (
    AskRequest,
    AskResponse,
    GenerateTestRequest,
    GenerateTestResponse,
    JDAnalysisResponse,
    JDUploadResponse,
    RunRequest,
    RunResponse,
    SubmitTestRequest,
    SubmitTestResponse,
)
from rag_core.session_logger import log_session

logger = logging.getLogger("codelens.api")
MAX_UPLOAD_BYTES = 2_000_000


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    init_clients()
    warm_retrieval()
    yield


app = FastAPI(
    title="CodeLens AI",
    description=(
        "Adaptive RAG assistant for JD-based interview readiness. "
        "Upload a job description to get each requirement explained and a study roadmap, "
        "then take a generated test. MCQs are scored in code, coding answers run in a "
        "sandbox, and guidance follows the full / hint / gentle / break judgment layer. "
        "Debugging help remains available through POST /ask."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# The Vite dev server is http://localhost:5173 (`npm run dev`) and
# http://localhost:4173 (`npm run preview`). 127.0.0.1 is listed too, because
# Windows browsers sometimes open that host instead of localhost. "*" keeps
# any other client, including the earlier student portal, able to call the API.
VITE_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", *VITE_DEV_ORIGINS],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "CodeLens AI is running",
        "description": "Adaptive RAG assistant for JD-based interview readiness",
        "modules": ["jd_understanding", "test_and_guide"],
    }


@app.post("/ask", response_model=AskResponse, tags=["guidance"])
def ask(request: AskRequest):
    result = run_pipeline(request.query, student_id=request.student_id, profile=request.profile)
    answer = result["answer"]
    if isinstance(answer, dict):
        answer = answer.get("answer", "No answer found")
    return AskResponse(
        student_id=request.student_id,
        query=result["query"],
        agent_used=result["agent_used"],
        answer=answer,
        directive=result["directive"],
        response_time=result.get("response_time", 0),
        profiling=result.get("profiling"),
    )


async def _read_upload(request: Request) -> tuple[bytes, str]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Expected a JSON object")
        text = body.get("text") or body.get("content") or ""
        if not isinstance(text, str):
            raise HTTPException(status_code=400, detail="text must be a string")
        filename = str(body.get("filename") or "jd.txt")
        return text.encode("utf-8"), filename

    form = await request.form()
    upload = form.get("file")
    if upload is not None and hasattr(upload, "read"):
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File is too large")
        return data, upload.filename or "upload.txt"
    text = form.get("text") or ""
    return str(text).encode("utf-8"), "jd.txt"


@app.post("/jd/upload", response_model=JDUploadResponse, tags=["jd"])
async def upload_jd(request: Request):
    raw, filename = await _read_upload(request)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")
    try:
        text = extract_text(raw, filename)
        jd_id = store_jd(text, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("jd upload failed")
        raise HTTPException(status_code=400, detail="Could not read that job description") from exc
    return JDUploadResponse(jd_id=jd_id)


@app.get("/jd/analyse/{jd_id}", response_model=JDAnalysisResponse, tags=["jd"])
def analyse(jd_id: str):
    try:
        return analyse_jd(jd_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Job description not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post(
    "/test/generate",
    response_model=GenerateTestResponse,
    response_model_exclude_none=True,
    tags=["test"],
)
def generate_test(body: GenerateTestRequest):
    try:
        return generate_questions(body.jd_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Job description not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/run", response_model=RunResponse, tags=["test"])
def run(body: RunRequest):
    result = run_code(body.code, language=body.language, stdin=body.stdin)
    return RunResponse(stdout=result["stdout"], stderr=result["stderr"])


@app.post("/test/submit", response_model=SubmitTestResponse, tags=["test"])
def submit_test(body: SubmitTestRequest):
    started = time.perf_counter()
    questions = load_questions(body.jd_id)
    if questions is None:
        raise HTTPException(status_code=404, detail="Generate a test for this job description first")

    report = evaluate_questions(questions, [answer.model_dump() for answer in body.answers])
    profile = diagnose(body.student_id, body.jd_id, report["results"], report["score"])
    try:
        roadmap = analyse_jd(body.jd_id)["roadmap"]
    except (LookupError, RuntimeError):
        roadmap = []
    guidance = build_guidance(
        student_id=body.student_id,
        profile=profile,
        failure_explanation=report["failure_explanation"],
        roadmap=roadmap,
    )
    topic = profile["weak_topics"][0] if profile["weak_topics"] else None
    pattern = profile["mistake_patterns"][0] if profile["mistake_patterns"] else ""
    log_session(
        student_id=body.student_id,
        query=f"Interview practice. {topic or 'review'} {pattern}".strip(),
        agent_used="guide",
        response_time=round(time.perf_counter() - started, 3),
        error_type=extract_error_type(pattern) if pattern else None,
        topic=topic,
    )
    return SubmitTestResponse(
        score=report["score"],
        weak_topics=profile["weak_topics"],
        guidance=guidance,
    )


@app.get("/pending-kb", tags=["knowledge-base"])
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
                "status": item[5],
            }
            for item in items
        ],
    }


@app.post("/approve-kb/{item_id}", tags=["knowledge-base"])
def approve_kb(item_id: int):
    success = approve_item(item_id)
    return {
        "message": f"Item {item_id} {'approved and added to KB' if success else 'not found'}"
    }


@app.post("/reject-kb/{item_id}", tags=["knowledge-base"])
def reject_kb(item_id: int):
    reject_item(item_id)
    return {"message": f"Item {item_id} rejected"}


@app.get("/sessions", tags=["guidance"])
def get_sessions():
    init_db()
    with connection() as conn:
        rows = [
            tuple(row)
            for row in conn.execute("SELECT * FROM sessions ORDER BY timestamp DESC").fetchall()
        ]
    return {
        "count": len(rows),
        "sessions": [
            {
                "id": row[0],
                "student_id": row[1],
                "query": row[2],
                "agent_used": row[3],
                "response_time": row[4],
                "timestamp": row[5],
                "error_type": row[6] if len(row) > 6 else None,
                "topic": row[7] if len(row) > 7 else None,
            }
            for row in rows
        ],
    }
