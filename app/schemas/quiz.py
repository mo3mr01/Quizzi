from pydantic import BaseModel, Field


class PDFUploadResponse(BaseModel):
    filename: str
    page_count: int
    text_length: int
    cleaned_length: int
    chunk_count: int
    message: str


class Question(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: int = Field(ge=0, le=3)
    difficulty: str = Field(pattern=r"^(easy|medium|hard)$")
    explanation: str | None = None


class QuizResponse(BaseModel):
    filename: str
    total_questions: int
    questions: list[Question]


class TrackEventRequest(BaseModel):
    event_name: str
    metadata: dict = {}


class TrackEventResponse(BaseModel):
    status: str = "ok"


class OverviewResponse(BaseModel):
    total_users: int
    total_quizzes: int
    total_uploads: int
