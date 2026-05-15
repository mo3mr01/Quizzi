import logging

from fastapi import HTTPException

from app.core.errors import QuizGenerationError
from app.schemas.quiz import Question, QuizResponse
from app.services.pdf_processor import extract_text_from_pdf
from app.services.text_cleaner import clean_text
from app.services.text_chunker import chunk_text
from app.services.groq_client import generate_quiz as groq_generate

logger = logging.getLogger("quiz_api")

PDF_PROCESSING_STEPS = ["extract", "clean", "chunk"]


async def generate_quiz_from_pdf(
    file_bytes: bytes,
    filename: str,
    user_id: str,
) -> QuizResponse:
    page_count = 0
    try:
        raw_text, page_count = extract_text_from_pdf(file_bytes)
        cleaned = clean_text(raw_text)
        chunks = chunk_text(cleaned)
    except Exception as e:
        logger.exception("PDF processing failed: filename=%s user_id=%s", filename, user_id)
        raise HTTPException(status_code=500, detail="Failed to process PDF file")

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from the PDF. Try a different file.",
        )

    try:
        raw_questions = await groq_generate(chunks[0])
    except QuizGenerationError as e:
        logger.error(
            "AI quiz generation failed after retries: filename=%s user_id=%s error=%s",
            filename, user_id, e.message,
        )
        raise HTTPException(
            status_code=502,
            detail="Quiz generation service temporarily unavailable. Please try again.",
        )

    if not raw_questions:
        raise HTTPException(
            status_code=502,
            detail="Quiz generation returned empty results. Please try again.",
        )

    questions = []
    for q in raw_questions:
        q.setdefault("explanation", None)
        questions.append(Question(**q))

    return QuizResponse(
        filename=filename,
        total_questions=len(questions),
        questions=questions,
    )
