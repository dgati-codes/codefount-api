"""
app/utils/exceptions.py
=========================
Global exception handlers registered on the FastAPI app.

Spring Boot equivalent
-----------------------
  @ControllerAdvice + @ExceptionHandler methods  (GlobalExceptionHandler.java)
  RequestValidationException  ≈  MethodArgumentNotValidException
  HTTPException               ≈  ResponseStatusException
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def _error_body(status_code: int, message: str, details=None) -> dict:
    body = {"status": status_code, "message": message}
    if details:
        body["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """
    Call this once in main.py — equivalent to Spring Boot auto-detecting
    all @ControllerAdvice beans on startup.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """
        Spring Boot: @ExceptionHandler(MethodArgumentNotValidException.class)
        Formats Pydantic field errors into a clean list.
        """
        errors = [
            {"field": " → ".join(str(loc) for loc in e["loc"]), "msg": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(422, "Validation failed", errors),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Catch unhandled ValueErrors bubbling past the service layer."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body(400, str(exc)),
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all — never expose internal stack traces in production.
        Spring Boot: @ExceptionHandler(Exception.class) with a 500 fallback.
        """
        import logging
        logging.getLogger("codefount").exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(500, "Internal server error"),
        )