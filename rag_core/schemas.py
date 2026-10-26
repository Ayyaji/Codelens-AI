"""Request and response models for the CodeLens API."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Directive = Literal["full", "hint", "gentle", "break"]
QuestionType = Literal["mcq", "coding"]
Role = Literal["student", "teacher"]
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _stripped(value: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError("must not be blank")
    return str(value).strip()


def normalize_email(value: str) -> str:
    cleaned = str(value or "").strip().lower()
    if not _EMAIL.match(cleaned):
        raise ValueError("invalid email")
    return cleaned


class UserPublic(BaseModel):
    id: str
    name: str
    email: str
    role: Role


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    email: str
    password: str
    role: Role | None = None

    @field_validator("name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        cleaned = _stripped(value)
        if len(cleaned) > 80:
            raise ValueError("name is too long")
        return cleaned

    @field_validator("email")
    @classmethod
    def email_ok(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def password_ok(cls, value: str) -> str:
        if not isinstance(value, str) or len(value) < 8 or len(value) > 72:
            raise ValueError("password must be 8 to 72 characters")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_ok(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def password_present(cls, value: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("must not be blank")
        return value


class AskRequest(BaseModel):
    """POST /ask — guidance chat. The student is the bearer token, not a body field."""

    model_config = ConfigDict(extra="ignore")

    query: str
    chat_id: str | None = None

    @field_validator("query")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)

    @field_validator("chat_id")
    @classmethod
    def blank_chat(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class AskResponse(BaseModel):
    answer: str
    agent_used: str
    directive: Directive
    chat_id: str


class JDUploadResponse(BaseModel):
    jd_id: str


class Skill(BaseModel):
    name: str
    level: str
    explanation: str

    @field_validator("name", "level", "explanation")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)


class RoadmapItem(BaseModel):
    order: int
    skill: str
    goal: str
    practice: str


class JDAnalysisResponse(BaseModel):
    skills: list[Skill]
    roadmap: list[RoadmapItem]


class GenerateTestRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jd_id: str

    @field_validator("jd_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)


class QuestionPublic(BaseModel):
    """A question safe to show a student. The answer key stays on the server."""

    id: str
    type: QuestionType
    skill: str
    prompt: str
    options: list[str] | None = None
    language: str | None = None
    starter_code: str | None = None
    sample_input: str | None = None
    sample_output: str | None = None


class GenerateTestResponse(BaseModel):
    jd_id: str
    questions: list[QuestionPublic]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    language: str = "python"
    # Sample input for the editor's Run button. Coding tasks read stdin.
    # Whitespace is kept: a trailing newline is part of the sample.
    stdin: str = ""

    @field_validator("code", "language")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)

    @field_validator("stdin", mode="before")
    @classmethod
    def stdin_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)


class RunResponse(BaseModel):
    stdout: str
    stderr: str


class AnswerSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question_id: str
    selected: str | None = None
    code: str | None = None
    language: str | None = None

    @field_validator("question_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)


class SubmitTestRequest(BaseModel):
    """The student is the bearer token. A client-supplied student id is ignored."""

    model_config = ConfigDict(extra="ignore")

    jd_id: str
    answers: list[AnswerSubmission] = Field(min_length=1)

    @field_validator("jd_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)


class Guidance(BaseModel):
    directive: Directive
    message: str
    next_steps: list[str]
    mistake_patterns: list[str] = []


class SubmitTestResponse(BaseModel):
    score: float = Field(ge=0, le=100)
    weak_topics: list[str]
    guidance: Guidance


class TestCase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stdin: str = Field(default="", alias="input")
    expected: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    directive: Directive | None = None
    agent_used: str | None = None
    ts: str


class ChatSummary(BaseModel):
    chat_id: str
    title: str
    updated_at: str


class ChatDetail(BaseModel):
    chat_id: str
    title: str
    messages: list[ChatMessage]


class ScoreEntry(BaseModel):
    test_id: str
    score: float
    created_at: str


class JDBrief(BaseModel):
    jd_id: str
    filename: str
    created_at: str


class PersonaResponse(BaseModel):
    weak_topics: list[str]
    mistake_patterns: list[str]
    scores: list[ScoreEntry]
    jds: list[JDBrief]


class HistoryTest(BaseModel):
    test_id: str
    score: float
    created_at: str


class HistoryResponse(BaseModel):
    jds: list[JDBrief]
    tests: list[HistoryTest]


class TeacherPersona(PersonaResponse):
    learning_notes: list[str] = []
    updated_at: str | None = None


class TeacherUser(BaseModel):
    id: str
    name: str
    email: str
    role: Role
    disabled: bool
    created_at: str | None = None


class ActivityItem(BaseModel):
    id: str
    type: str
    detail: dict
    ts: str
    user_id: str | None = None
    name: str | None = None
    email: str | None = None


class StudentDetail(BaseModel):
    user: TeacherUser
    persona: TeacherPersona
    recent_activity: list[ActivityItem]
    tests: list[HistoryTest]


class StudentSummary(BaseModel):
    id: str
    name: str
    email: str
    disabled: bool
    last_active: str | None = None
    avg_score: float | None = None
    weak_topics: list[str]


class DirectiveCounts(BaseModel):
    """`break` is a Python keyword, so the field is aliased on the wire."""

    model_config = ConfigDict(populate_by_name=True)

    full: int = 0
    hint: int = 0
    gentle: int = 0
    break_: int = Field(default=0, alias="break")


class OverviewResponse(BaseModel):
    total_students: int
    active_today: int
    avg_score: float
    directive_counts: DirectiveCounts
    pending_kb: int


class DisableRequest(BaseModel):
    disabled: bool


class ResetResponse(BaseModel):
    id: str
    reset: bool = True


class KBItem(BaseModel):
    id: str
    content: str
    source: str | None = None
    proposed_by: str | None = None
    status: Literal["pending", "approved", "rejected"]
    query: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None


class KBEdit(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)


class StoredQuestion(BaseModel):
    """Full question, including the key used by the evaluator."""

    id: str
    type: QuestionType
    skill: str
    prompt: str
    options: list[str] = []
    answer: str | None = None
    language: str = "python"
    starter_code: str = ""
    test_cases: list[TestCase] = []
