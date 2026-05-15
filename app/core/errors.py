from fastapi.responses import JSONResponse


def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": message},
    )


class QuizGenerationError(Exception):
    def __init__(self, message: str = "Quiz generation failed"):
        self.message = message
        super().__init__(self.message)
