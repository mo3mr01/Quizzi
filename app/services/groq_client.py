import asyncio
import json
import logging
import re

from groq import AsyncGroq

from app.core.config import settings
from app.core.context import request_id_var
from app.core.errors import QuizGenerationError
from app.schemas.quiz import Question

logger = logging.getLogger("quiz_api")

client = AsyncGroq(api_key=settings.groq_api_key)

QUIZ_SYSTEM_PROMPT = """You are a precise quiz generator. Generate exactly 20 multiple-choice questions in strict JSON format.

RULES:
- Generate exactly 20 questions.
- Questions must cover only main concepts from the provided text.
- NO headings, NO introductory text, NO summaries in the output.
- Focus on meaningful, testable knowledge only.

DIFFICULTY DISTRIBUTION:
- 6 easy questions
- 8 medium questions
- 6 hard questions

QUALITY GUIDELINES:
- Keep correct and incorrect options similar in length.
- Avoid obviously correct answers — all options should be plausible.
- Avoid ambiguity. Each question must have exactly one clearly correct answer.
- Avoid overly long correct answers compared to distractors.

QUESTION VARIETY:
- Include conceptual questions (understanding of ideas)
- Reasoning questions (apply logic to reach conclusion)
- Application questions (apply knowledge to new scenarios)
- Definitions only where necessary

OUTPUT FORMAT (STRICT JSON ONLY - no markdown, no code fences):
{
  "questions": [
    {
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_answer": 0,
      "difficulty": "easy",
      "explanation": "string"
    }
  ]
}

- correct_answer is the 0-based index (0, 1, 2, or 3) of the correct option.
- difficulty must be exactly "easy", "medium", or "hard".
- explanation is a brief 1-2 sentence explanation of the correct answer.
"""


def _safe_parse_ai_response(raw: str) -> list[dict] | None:
    if not raw or not raw.strip():
        logger.warning("AI returned empty response")
        return None

    strategy = "direct"
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "questions" in data:
            if isinstance(data["questions"], list):
                return data["questions"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    strategy = "code_fence"
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and "questions" in data:
                if isinstance(data["questions"], list):
                    return data["questions"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    strategy = "regex_obj"
    match = re.search(r"\{[\s\S]*\"questions\"[\s\S]*\}", raw)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict) and "questions" in data:
                if isinstance(data["questions"], list):
                    return data["questions"]
        except json.JSONDecodeError:
            pass

    logger.warning("All AI response parsing strategies failed. Strategy=%s", strategy)
    return None


def _validate_questions(raw_questions: list[dict]) -> list[dict]:
    """Validate each question against the Pydantic Question schema.

    Filters out malformed questions silently, logs a warning for each.
    """
    valid = []
    for i, q in enumerate(raw_questions):
        try:
            Question(**q)
            valid.append(q)
        except Exception as e:
            logger.warning(
                "Question %d failed validation: %s | data=%s",
                i, e, {k: v for k, v in q.items() if k in ("question", "difficulty")},
            )
    return valid


async def generate_quiz(text: str) -> list[dict]:
    """Generate quiz questions from text with full safety layer.

    - Retries up to groq_max_retries times on failure
    - Timeout enforced via asyncio.wait_for
    - Multi-strategy JSON parsing
    - Per-question Pydantic validation
    - Returns only valid questions; raises QuizGenerationError if all fail
    """
    rid = request_id_var.get() or "-"
    last_error: str | None = None

    for attempt in range(settings.groq_max_retries + 1):
        logger.info(
            "Groq generation attempt %d/%d | request_id=%s",
            attempt + 1, settings.groq_max_retries + 1, rid,
        )

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"Generate exactly {settings.max_questions} quiz questions based on this text:\n\n{text}",
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                ),
                timeout=settings.groq_timeout_seconds,
            )
        except asyncio.TimeoutError:
            last_error = f"Groq API timed out after {settings.groq_timeout_seconds}s"
            logger.warning("%s | attempt=%d", last_error, attempt + 1)
            if attempt < settings.groq_max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %ds...", wait)
                await asyncio.sleep(wait)
            continue
        except Exception as e:
            last_error = f"Groq API call failed: {e}"
            logger.warning("%s | attempt=%d", last_error, attempt + 1, exc_info=True)
            if attempt < settings.groq_max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %ds...", wait)
                await asyncio.sleep(wait)
            continue

        raw = response.choices[0].message.content
        questions = _safe_parse_ai_response(raw)

        if questions is None:
            last_error = "AI returned malformed or unparseable JSON"
            logger.warning("%s | attempt=%d | raw_preview=%s", last_error, attempt + 1, raw[:200] if raw else "empty")
            if attempt < settings.groq_max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %ds...", wait)
                await asyncio.sleep(wait)
            continue

        validated = _validate_questions(questions)

        if not validated:
            last_error = "AI returned zero valid questions after validation"
            logger.warning("%s | attempt=%d | raw_count=%d", last_error, attempt + 1, len(questions))
            if attempt < settings.groq_max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %ds...", wait)
                await asyncio.sleep(wait)
            continue

        logger.info(
            "Groq success | attempt=%d | valid=%d/%d | request_id=%s",
            attempt + 1, len(validated), len(questions), rid,
        )
        return validated

    logger.error(
        "Groq generation exhausted all %d attempts | last_error=%s | request_id=%s",
        settings.groq_max_retries + 1, last_error, rid,
    )
    raise QuizGenerationError("Failed to generate quiz questions after multiple attempts")
