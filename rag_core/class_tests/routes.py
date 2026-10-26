"""HTTP routes for teacher-authored timed tests.

``/test/*`` is the job-description practice flow and is not handled here.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from rag_core.auth import current_teacher, current_user
from rag_core.class_tests.errors import ClassTestError
from rag_core.class_tests.generate import generate_drafts
from rag_core.class_tests.parse_mcq import parse_mcq_import
from rag_core.class_tests.service import (
    attempts_csv,
    attempts_for_teacher,
    create_test,
    delete_test,
    duplicate_test,
    get_test_for_teacher,
    list_bank,
    list_tests_for_student,
    list_tests_for_teacher,
    record_focus_loss,
    run_question,
    save_answers,
    save_bank_questions,
    start_attempt,
    student_test,
    submit_attempt,
    update_test,
)

router = APIRouter(tags=["class-tests"])


class ClassTestBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    description: str | None = None
    topic: str | None = None
    test_type: str | None = None
    duration_minutes: int | None = None
    available_from: str | None = None
    available_until: str | None = None
    published: bool | None = None
    allow_retake: bool | None = None
    show_answers_after_submit: bool | None = None
    shuffle_questions: bool | None = None
    shuffle_options: bool | None = None
    questions: list[dict] | None = None


class ImportBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = ""
    questions: list[dict] | None = None


class AnswerBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answers: list[dict] | None = None


class RunBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question_id: str = ""
    code: str = ""
    language: str = "python"


class GenerateBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    syllabus: str = ""
    topic: str | None = None
    difficulty: str = "medium"
    mcq_count: int = 0
    coding_count: int = 0
    language: str = "python"
    use_kb: bool = False
    avoid: list[str] = Field(default_factory=list)


class BankSaveBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    questions: list[dict] | None = None


def _student(user: dict) -> dict:
    if user.get("role") != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return user


def _raise(exc: ClassTestError) -> None:
    raise HTTPException(status_code=exc.status, detail=exc.detail) from None


@router.get("/teacher/question-bank")
async def teacher_question_bank(kind: str = "", topic: str = "", teacher: dict = Depends(current_teacher)):
    del teacher
    return await list_bank(kind, topic)


@router.post("/teacher/question-bank")
async def teacher_save_question_bank(body: BankSaveBody, teacher: dict = Depends(current_teacher)):
    try:
        return await save_bank_questions(teacher["id"], body.questions)
    except ClassTestError as exc:
        _raise(exc)


@router.post("/teacher/question-bank/import")
async def teacher_import_mcq(body: ImportBody, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        questions = parse_mcq_import(text=body.text, questions=body.questions)
    except ClassTestError as exc:
        _raise(exc)
    return {"questions": questions}


@router.get("/teacher/class-tests")
async def teacher_list_class_tests(teacher: dict = Depends(current_teacher)):
    del teacher
    return await list_tests_for_teacher()


@router.post("/teacher/class-tests/generate")
async def teacher_generate_questions(body: GenerateBody, teacher: dict = Depends(current_teacher)):
    """Draft questions for the editor. Nothing is stored or published."""
    del teacher
    import asyncio

    try:
        return await asyncio.to_thread(generate_drafts, body.model_dump())
    except ClassTestError as exc:
        _raise(exc)


@router.post("/teacher/class-tests")
async def teacher_create_class_test(body: ClassTestBody, teacher: dict = Depends(current_teacher)):
    try:
        return await create_test(teacher["id"], body.model_dump(exclude_unset=True))
    except ClassTestError as exc:
        _raise(exc)


@router.get("/teacher/class-tests/{test_id}")
async def teacher_get_class_test(test_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        return await get_test_for_teacher(test_id)
    except ClassTestError as exc:
        _raise(exc)


@router.put("/teacher/class-tests/{test_id}")
async def teacher_update_class_test(test_id: str, body: ClassTestBody, teacher: dict = Depends(current_teacher)):
    try:
        return await update_test(test_id, teacher["id"], body.model_dump(exclude_unset=True))
    except ClassTestError as exc:
        _raise(exc)


@router.delete("/teacher/class-tests/{test_id}")
async def teacher_delete_class_test(test_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        return await delete_test(test_id)
    except ClassTestError as exc:
        _raise(exc)


@router.post("/teacher/class-tests/{test_id}/duplicate")
async def teacher_duplicate_class_test(test_id: str, teacher: dict = Depends(current_teacher)):
    try:
        return await duplicate_test(test_id, teacher["id"])
    except ClassTestError as exc:
        _raise(exc)


@router.get("/teacher/class-tests/{test_id}/attempts")
async def teacher_class_attempts(test_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        return await attempts_for_teacher(test_id)
    except ClassTestError as exc:
        _raise(exc)


@router.get("/teacher/class-tests/{test_id}/attempts.csv")
async def teacher_class_attempts_csv(test_id: str, teacher: dict = Depends(current_teacher)):
    del teacher
    try:
        report = await attempts_for_teacher(test_id)
    except ClassTestError as exc:
        _raise(exc)
    filename = f"class-test-{test_id}-scores.csv"
    return Response(
        content=attempts_csv(report),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/class-tests")
async def student_list_class_tests(include_upcoming: bool = False, user: dict = Depends(current_user)):
    _student(user)
    return await list_tests_for_student(user["id"], include_upcoming=include_upcoming)


@router.get("/class-tests/{test_id}")
async def student_get_class_test(test_id: str, user: dict = Depends(current_user)):
    _student(user)
    try:
        return await student_test(user["id"], test_id)
    except ClassTestError as exc:
        _raise(exc)


@router.post("/class-tests/{test_id}/start")
async def student_start_class_test(test_id: str, user: dict = Depends(current_user)):
    _student(user)
    try:
        return await start_attempt(user["id"], test_id)
    except ClassTestError as exc:
        _raise(exc)


@router.put("/class-tests/{test_id}/answers")
async def student_save_class_answers(test_id: str, body: AnswerBody, user: dict = Depends(current_user)):
    _student(user)
    try:
        return await save_answers(user["id"], test_id, body.answers)
    except ClassTestError as exc:
        _raise(exc)


@router.post("/class-tests/{test_id}/focus")
async def student_focus_loss(test_id: str, user: dict = Depends(current_user)):
    _student(user)
    try:
        return await record_focus_loss(user["id"], test_id)
    except ClassTestError as exc:
        _raise(exc)


@router.post("/class-tests/{test_id}/run")
async def student_run_class_code(test_id: str, body: RunBody, user: dict = Depends(current_user)):
    _student(user)
    try:
        return await run_question(user["id"], test_id, body.model_dump())
    except ClassTestError as exc:
        _raise(exc)


@router.post("/class-tests/{test_id}/submit")
async def student_submit_class_test(test_id: str, body: AnswerBody, user: dict = Depends(current_user)):
    _student(user)
    try:
        return await submit_attempt(user["id"], test_id, body.answers)
    except ClassTestError as exc:
        _raise(exc)
