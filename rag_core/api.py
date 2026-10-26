"""CodeLens AI HTTP API.

Accounts, chats, personas, job descriptions, tests, and the knowledge-base
queue are stored in MongoDB. Chroma remains the vector index. Student routes
use the bearer token's user. Teacher routes are the only way a proposed note
is written into that index.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

from rag_core.agents.diagnoser import diagnose
from rag_core.agents.evaluator import evaluate_questions
from rag_core.agents.guide import build_guidance
from rag_core.agents.jd_analyser import analyse_jd, extract_text, store_jd
from rag_core.agents.question_gen import generate_questions, load_questions
from rag_core.agents.retrieval import warm_retrieval
from rag_core.auth import (
    create_token,
    current_teacher,
    current_user,
    hash_password,
    public_user,
    verify_password,
    warn_default_secret,
)
from rag_core.config import cors_origin_regex, cors_origins
from rag_core.judgment import extract_error_type
from rag_core.kb_fields import KBInputError
from rag_core.kb_files import UploadRejected
from rag_core.kb_update import (
    ChromaError,
    MissingUpload,
    approve_pending,
    approve_upload,
    bulk_review,
    create_kb_item,
    delete_kb_item,
    discard_upload,
    edit_kb,
    pending_items,
    reject_pending,
    save_upload,
    search_library,
    uploads,
)
from rag_core.llm import AIBusy, init_clients
from rag_core.mongo import close_mongo, ping
from rag_core.pipeline import run_pipeline
from rag_core.class_tests.routes import router as class_test_router
from rag_core.sandbox.runner import run_code
from rag_core.schemas import (
    ActivityItem,
    AskRequest,
    AskResponse,
    AuthResponse,
    ChatDetail,
    ChatSummary,
    DisableRequest,
    GenerateTestRequest,
    GenerateTestResponse,
    HistoryResponse,
    JDAnalysisResponse,
    JDUploadResponse,
    KBBulkRequest,
    KBBulkResponse,
    KBCreate,
    KBDeleted,
    KBItem,
    KBLibraryPage,
    KBPatch,
    KBReject,
    KBUpload,
    KBUploadApprove,
    KBUploadApproved,
    LoginRequest,
    OverviewResponse,
    PersonaResponse,
    RegisterRequest,
    ResetResponse,
    RunRequest,
    RunResponse,
    StudentDetail,
    StudentSummary,
    SubmitTestRequest,
    SubmitTestResponse,
    UserPublic,
)
from rag_core.session_logger import log_session
from rag_core.store import (
    activity_feed,
    add_activity,
    chat_detail,
    create_user,
    find_user_by_email,
    history_view,
    list_chats,
    persona_view,
    save_turn,
    set_disabled,
    find_kb,
    kb_public_one,
    student_detail,
    student_row,
    student_rows,
    teacher_overview,
    wipe_student,
)

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
    warn_default_secret()
    logger.info("cors origins=%s", ",".join(cors_origins()))
    await ping()
    init_clients()
    warm_retrieval()
    yield
    await close_mongo()


app = FastAPI(
    title="CodeLens AI",
    description=(
        "Adaptive RAG assistant for JD-based interview readiness. "
        "Students register, upload a job description, and practise against it. "
        "Teachers review the class and approve anything before it enters the knowledge base."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

class _UnhandledErrorMiddleware:
    """JSON 500 for errors that escape the route handlers.

    Starlette's ServerErrorMiddleware is the outermost layer and re-raises
    after writing the 500, so that response never passes through CORS. The
    browser then reports a network error and hides ``detail``. This layer
    sits inside CORSMiddleware, writes a generic JSON body, and does not
    re-raise. The exception text stays in the server log.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def track(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, track)
        except Exception as exc:
            if started:
                raise
            logger.exception("unhandled error (%s)", type(exc).__name__)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Something went wrong. Please try again."},
            )
            await response(scope, receive, send)


# Bearer tokens are headers, not cookies, so credentials stay off.
# The three-server deploy is same-origin: Nginx on the frontend proxies /api
# and the browser never calls port 8000. The simple deploy is not: the site
# is on Vercel and the API is on another host. CORS_ORIGIN_REGEX allows
# https://*.vercel.app, and CORS_ORIGINS lists any extra site (CloudFront,
# or a custom domain). With both unset, local development allows any origin.
# ``add_middleware`` inserts at the front, so the error layer is registered
# first and CORS stays outside it.
app.add_middleware(_UnhandledErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=cors_origin_regex(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(class_test_router)


@app.exception_handler(AIBusy)
async def ai_busy(_request: Request, exc: AIBusy):
    """503 when every Groq key is rate-limited. CORS still wraps this response."""
    return JSONResponse(status_code=503, content={"detail": exc.detail})


def _text_answer(answer) -> str:
    if isinstance(answer, dict):
        answer = answer.get("answer", "")
    text = "" if answer is None else str(answer)
    return text or "No answer found"


def _auth_response(user: dict, token: str) -> AuthResponse:
    return AuthResponse(token=token, user=UserPublic(**public_user(user)))


@app.get("/")
def root():
    return {
        "message": "CodeLens AI is running",
        "description": "Adaptive RAG assistant for JD-based interview readiness",
        "modules": ["auth", "jd_understanding", "test_and_guide", "class_tests", "teacher"],
    }


@app.get("/health", tags=["meta"])
async def health():
    """Liveness and MongoDB reachability. No authentication, no model load.

    The frontend Nginx proxies ``/api/health`` here, and Docker uses it
    directly. A MongoDB failure is 503 so the container is not marked healthy
    while the database is unreachable. The body never includes the URI.
    """
    try:
        await ping(quiet=True)
    except Exception as exc:
        logger.warning("health check: mongodb unreachable (%s)", type(exc).__name__)
        return JSONResponse({"status": "degraded", "mongo": "error"}, status_code=503)
    return {"status": "ok", "mongo": "ok"}


@app.post("/auth/register", response_model=AuthResponse, tags=["auth"])
async def register(body: RegisterRequest):
    if body.role == "teacher":
        raise HTTPException(status_code=403, detail="Teachers cannot self-register")
    existing = await find_user_by_email(body.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")
    try:
        user = await create_user(body.name, body.email, await hash_password(body.password), role="student")
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email is already registered") from None
    user_id = str(user["_id"])
    await add_activity(user_id, "register", {})
    return _auth_response(user, create_token(user_id, "student"))


@app.post("/auth/login", response_model=AuthResponse, tags=["auth"])
async def login(body: LoginRequest):
    user = await find_user_by_email(body.email)
    if user is None or not await verify_password(body.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("disabled"):
        raise HTTPException(status_code=403, detail="Account disabled")
    user_id = str(user["_id"])
    await add_activity(user_id, "login", {})
    return _auth_response(user, create_token(user_id, user["role"]))


@app.get("/auth/me", response_model=UserPublic, tags=["auth"])
async def me(user: dict = Depends(current_user)):
    return UserPublic(**public_user(user))


@app.post("/ask", response_model=AskResponse, tags=["guidance"])
async def ask(body: AskRequest, user: dict = Depends(current_user)):
    result = await run_pipeline(body.query, student_id=user["id"])
    answer = _text_answer(result.get("answer"))
    try:
        chat_id = await save_turn(
            user["id"],
            body.chat_id,
            body.query,
            answer,
            result["directive"],
            result["agent_used"],
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Chat not found") from None
    return AskResponse(
        answer=answer,
        agent_used=result["agent_used"],
        directive=result["directive"],
        chat_id=chat_id,
    )


@app.get("/me/chats", response_model=list[ChatSummary], tags=["me"])
async def my_chats(user: dict = Depends(current_user)):
    return await list_chats(user["id"])


@app.get("/me/chats/{chat_id}", response_model=ChatDetail, tags=["me"])
async def my_chat(chat_id: str, user: dict = Depends(current_user)):
    detail = await chat_detail(user["id"], chat_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return detail


@app.get("/me/persona", response_model=PersonaResponse, tags=["me"])
async def my_persona(user: dict = Depends(current_user)):
    return await persona_view(user["id"])


@app.get("/me/history", response_model=HistoryResponse, tags=["me"])
async def my_history(user: dict = Depends(current_user)):
    return await history_view(user["id"])


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
async def upload_jd(request: Request, user: dict = Depends(current_user)):
    raw, filename = await _read_upload(request)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")
    try:
        text = extract_text(raw, filename)
        jd_id = await store_jd(text, filename, user["id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("jd upload failed")
        raise HTTPException(status_code=400, detail="Could not read that job description") from exc
    await add_activity(user["id"], "jd_upload", {"jd_id": jd_id, "filename": filename})
    return JDUploadResponse(jd_id=jd_id)


@app.get("/jd/analyse/{jd_id}", response_model=JDAnalysisResponse, tags=["jd"])
async def analyse(jd_id: str, user: dict = Depends(current_user)):
    try:
        result = await analyse_jd(jd_id, user["id"])
    except LookupError:
        raise HTTPException(status_code=404, detail="Job description not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await add_activity(user["id"], "jd_analyse", {"jd_id": jd_id})
    return result


@app.post(
    "/test/generate",
    response_model=GenerateTestResponse,
    response_model_exclude_none=True,
    tags=["test"],
)
async def generate_test(body: GenerateTestRequest, user: dict = Depends(current_user)):
    try:
        generated = await generate_questions(body.jd_id, user["id"])
    except LookupError:
        raise HTTPException(status_code=404, detail="Job description not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await add_activity(
        user["id"],
        "test_generate",
        {"jd_id": body.jd_id, "questions": len(generated.get("questions") or [])},
    )
    return generated


@app.post("/run", response_model=RunResponse, tags=["test"])
async def run(body: RunRequest, user: dict = Depends(current_user)):
    result = await asyncio.to_thread(run_code, body.code, body.language, body.stdin)
    await add_activity(
        user["id"],
        "run",
        {"language": body.language, "code_chars": len(body.code)},
    )
    return RunResponse(stdout=result["stdout"], stderr=result["stderr"])


@app.post("/test/submit", response_model=SubmitTestResponse, tags=["test"])
async def submit_test(body: SubmitTestRequest, user: dict = Depends(current_user)):
    started = time.perf_counter()
    try:
        questions = await load_questions(body.jd_id, user["id"])
    except LookupError:
        raise HTTPException(status_code=404, detail="Job description not found") from None
    if questions is None:
        raise HTTPException(status_code=404, detail="Generate a test for this job description first")

    report = await asyncio.to_thread(
        evaluate_questions,
        questions,
        [answer.model_dump() for answer in body.answers],
    )
    profile = await diagnose(
        user["id"],
        body.jd_id,
        report["results"],
        report["score"],
        answers=[answer.model_dump() for answer in body.answers],
    )
    try:
        roadmap = (await analyse_jd(body.jd_id, user["id"]))["roadmap"]
    except (LookupError, RuntimeError):
        roadmap = []
    guidance = await build_guidance(
        student_id=user["id"],
        profile=profile,
        failure_explanation=report["failure_explanation"],
        roadmap=roadmap,
    )
    topic = profile["weak_topics"][0] if profile["weak_topics"] else None
    pattern = profile["mistake_patterns"][0] if profile["mistake_patterns"] else ""
    await log_session(
        student_id=user["id"],
        query=f"Interview practice. {topic or 'review'} {pattern}".strip(),
        agent_used="guide",
        response_time=round(time.perf_counter() - started, 3),
        error_type=extract_error_type(pattern) if pattern else None,
        topic=topic,
        activity_type="test_submit",
        directive=guidance["directive"],
        extra={"score": report["score"], "jd_id": body.jd_id, "test_id": profile.get("test_id")},
    )
    return SubmitTestResponse(
        score=report["score"],
        weak_topics=profile["weak_topics"],
        guidance=guidance,
    )


@app.get("/teacher/overview", response_model=OverviewResponse, tags=["teacher"])
async def overview(teacher: dict = Depends(current_teacher)):
    del teacher
    return await teacher_overview()


@app.get("/teacher/students", response_model=list[StudentSummary], tags=["teacher"])
async def students(teacher: dict = Depends(current_teacher)):
    del teacher
    return await student_rows()


@app.get("/teacher/students/{student_id}", response_model=StudentDetail, tags=["teacher"])
async def student(student_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    detail = await student_detail(student_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return detail


@app.get("/teacher/students/{student_id}/chats", response_model=list[ChatSummary], tags=["teacher"])
async def student_chats(student_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    if await student_detail(student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return await list_chats(student_id)


@app.get(
    "/teacher/students/{student_id}/chats/{chat_id}",
    response_model=ChatDetail,
    tags=["teacher"],
)
async def student_chat(student_id: str, chat_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    if await student_detail(student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    detail = await chat_detail(student_id, chat_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return detail


@app.patch("/teacher/students/{student_id}", response_model=StudentSummary, tags=["teacher"])
async def patch_student(student_id: str, body: DisableRequest, teacher: dict = Depends(current_teacher)):
    if not await set_disabled(student_id, body.disabled):
        raise HTTPException(status_code=404, detail="Student not found")
    await add_activity(
        student_id,
        "account",
        {"action": "disabled" if body.disabled else "enabled", "by": teacher["id"]},
    )
    row = await student_row(student_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return row


@app.post("/teacher/students/{student_id}/reset", response_model=ResetResponse, tags=["teacher"])
async def reset_student(student_id: str, teacher: dict = Depends(current_teacher)):
    if await student_detail(student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    await wipe_student(student_id)
    await add_activity(student_id, "account", {"action": "reset", "by": teacher["id"]})
    return ResetResponse(id=student_id, reset=True)


@app.get("/teacher/activity", response_model=list[ActivityItem], tags=["teacher"])
async def teacher_activity(
    limit: int = Query(default=50, ge=1, le=200),
    teacher: dict = Depends(current_teacher),
):
    del teacher
    return await activity_feed(limit)


def _kb_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KBInputError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, MissingUpload):
        return HTTPException(status_code=404, detail="Upload not found")
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail="Knowledge item not found")
    if isinstance(exc, ChromaError):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=500, detail="Knowledge base request failed")


@app.get("/teacher/kb/pending", response_model=list[KBItem], tags=["teacher"])
async def teacher_pending_kb(teacher: dict = Depends(current_teacher)):
    del teacher
    return await pending_items()


@app.get("/teacher/kb", response_model=KBLibraryPage, tags=["teacher"])
async def teacher_search_kb(
    q: str = "",
    status: str = "",
    topic: str = "",
    tag: str = "",
    note_type: str = Query(default="", alias="type"),
    source: str = "",
    created_from: str = Query(default="", alias="from"),
    to: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=8, ge=1, le=50),
    teacher: dict = Depends(current_teacher),
):
    del teacher
    try:
        return await search_library(
            {
                "q": q,
                "status": status,
                "topic": topic,
                "tag": tag,
                "type": note_type,
                "source": source,
                "from": created_from,
                "to": to,
                "page": page,
                "page_size": page_size,
            }
        )
    except KBInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/teacher/kb", response_model=KBItem, tags=["teacher"])
async def teacher_create_kb(body: KBCreate, teacher: dict = Depends(current_teacher)):
    try:
        return await create_kb_item(teacher, body.model_dump(exclude_unset=True))
    except KBInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChromaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/teacher/kb/bulk", response_model=KBBulkResponse, tags=["teacher"])
async def teacher_bulk_kb(body: KBBulkRequest, teacher: dict = Depends(current_teacher)):
    try:
        return await bulk_review(teacher, body.ids, body.action, body.reason)
    except KBInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/teacher/kb/uploads", response_model=list[KBUpload], tags=["teacher"])
async def teacher_list_uploads(teacher: dict = Depends(current_teacher)):
    del teacher
    return await uploads()


@app.post("/teacher/kb/uploads", response_model=KBUpload, tags=["teacher"])
async def teacher_create_upload(request: Request, teacher: dict = Depends(current_teacher)):
    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise HTTPException(status_code=422, detail="Choose a file.")
    raw = await upload.read()
    media = getattr(upload, "content_type", None) or ""
    try:
        return await save_upload(teacher, getattr(upload, "filename", None), media, raw)
    except UploadRejected as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc


@app.post("/teacher/kb/uploads/{upload_id}/approve", response_model=KBUploadApproved, tags=["teacher"])
async def teacher_approve_upload(upload_id: str, body: KBUploadApprove, teacher: dict = Depends(current_teacher)):
    try:
        return await approve_upload(teacher, upload_id, body.model_dump(exclude_unset=True))
    except Exception as exc:
        if isinstance(exc, (KBInputError, MissingUpload, LookupError, ChromaError, ValueError)):
            raise _kb_error(exc) from exc
        logger.exception("upload approval failed")
        raise HTTPException(status_code=502, detail="Could not write to the knowledge base") from exc


@app.delete("/teacher/kb/uploads/{upload_id}", response_model=KBDeleted, tags=["teacher"])
async def teacher_discard_upload(upload_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        return await discard_upload(upload_id)
    except Exception as exc:
        if isinstance(exc, (MissingUpload, ValueError)):
            raise _kb_error(exc) from exc
        raise


@app.get("/teacher/kb/{item_id}", response_model=KBItem, tags=["teacher"])
async def teacher_get_kb(item_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    doc = await find_kb(item_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return await kb_public_one(doc)


@app.put("/teacher/kb/{item_id}", response_model=KBItem, tags=["teacher"])
async def teacher_edit_kb(item_id: str, body: KBPatch, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        return await edit_kb(item_id, body.model_dump(exclude_unset=True))
    except LookupError:
        raise HTTPException(status_code=404, detail="Pending item not found") from None
    except KBInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ChromaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.delete("/teacher/kb/{item_id}", response_model=KBDeleted, tags=["teacher"])
async def teacher_delete_kb(item_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        return await delete_kb_item(item_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Knowledge item not found") from None
    except ChromaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/teacher/kb/{item_id}/approve", response_model=KBItem, tags=["teacher"])
async def teacher_approve_kb(item_id: str, teacher: dict = Depends(current_teacher)):
    try:
        return await approve_pending(item_id, teacher["id"])
    except LookupError:
        raise HTTPException(status_code=404, detail="Pending item not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ChromaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/teacher/kb/{item_id}/reject", response_model=KBItem, tags=["teacher"])
async def teacher_reject_kb(
    item_id: str,
    body: KBReject | None = None,
    teacher: dict = Depends(current_teacher),
):
    reason = None if body is None else body.reason
    try:
        return await reject_pending(item_id, teacher["id"], reason)
    except LookupError:
        raise HTTPException(status_code=404, detail="Pending item not found") from None
    except KBInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
