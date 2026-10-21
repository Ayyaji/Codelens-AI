"""Request and response models for the CodeLens API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Directive = Literal["full", "hint", "gentle", "break"]
QuestionType = Literal["mcq", "coding"]


def _stripped(value: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError("must not be blank")
    return str(value).strip()


class AskRequest(BaseModel):
    """POST /ask — guidance chat, including debugging help."""

    model_config = ConfigDict(extra="ignore")

    student_id: str
    query: str
    profile: bool = False

    @field_validator("student_id", "query")
    @classmethod
    def not_blank(cls, value: str) -> str:
        return _stripped(value)


class AskResponse(BaseModel):
    answer: str
    agent_used: str
    directive: Directive
    student_id: str | None = None
    query: str | None = None
    response_time: float = 0
    profiling: dict | None = None


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
    model_config = ConfigDict(extra="ignore")

    student_id: str
    jd_id: str
    answers: list[AnswerSubmission] = Field(min_length=1)

    @field_validator("student_id", "jd_id")
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
