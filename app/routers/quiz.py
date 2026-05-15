from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.auth import get_current_user
from app.schemas.quiz import PDFUploadResponse, QuizResponse
from app.services.pdf_processor import extract_text_from_pdf
from app.services.text_cleaner import clean_text
from app.services.text_chunker import chunk_text
from app.services.quiz_service import generate_quiz_from_pdf
from app.services.usage_service import check_and_increment_quiz_usage, get_usage_stats

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/upload-pdf", response_model=PDFUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        file_bytes = await file.read()
        raw_text, page_count = extract_text_from_pdf(file_bytes)
        cleaned = clean_text(raw_text)
        chunks = chunk_text(cleaned)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process PDF file")

    return PDFUploadResponse(
        filename=file.filename,
        page_count=page_count,
        text_length=len(raw_text),
        cleaned_length=len(cleaned),
        chunk_count=len(chunks),
        message=f"Extracted {len(raw_text)} chars, cleaned to {len(cleaned)} chars, split into {len(chunks)} chunk(s)",
    )


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        allowed = await check_and_increment_quiz_usage(user_id)
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to verify usage limit. Please try again.")

    if not allowed:
        stats = await get_usage_stats(user_id)
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily quiz generation limit reached. Try again tomorrow.",
                "limit": stats["limit"],
                "used": stats["used"],
                "resets_on": stats["date"],
            },
        )

    file_bytes = await file.read()
    return await generate_quiz_from_pdf(file_bytes, file.filename, user_id)


@router.get("/usage")
async def get_usage(
    user_id: str = Depends(get_current_user),
):
    return await get_usage_stats(user_id)
