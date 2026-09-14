"""
Standardized error envelopes and global exception handlers.
Prevents internal tracebacks, SQL statements, and raw error leaks to clients.
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.logging import get_logger, get_request_id

logger = get_logger("app.core.exceptions")


# ---------------------------------------------------------------------------
# Custom Exception Hierarchy
# ---------------------------------------------------------------------------


class AppBaseException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class DatabaseUnavailableError(AppBaseException):
    """Raised when Postgres or connection pool is unreachable."""

    def __init__(
        self,
        message: str = "The database is currently unreachable. Please ensure the PostgreSQL container is running.",
    ):
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class OllamaUnavailableError(AppBaseException):
    """Raised when the local Ollama daemon is offline or unreachable."""

    def __init__(
        self,
        message: str = "The local Ollama inference service is offline or unreachable on port 11434. Please ensure Ollama is running ('ollama serve').",
    ):
        super().__init__(
            message=message,
            code="OLLAMA_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class InferenceFailedError(AppBaseException):
    """Raised when both cloud and fallback LLM inference fail."""

    def __init__(
        self,
        message: str = "Inference generation failed across all available local and cloud providers.",
    ):
        super().__init__(
            message=message,
            code="INFERENCE_FAILED",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class SessionNotFoundError(AppBaseException):
    """Raised when a requested session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session '{session_id}' not found",
            code="SESSION_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


# ---------------------------------------------------------------------------
# Standard Error Envelope Factory
# ---------------------------------------------------------------------------


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    extra_details: Optional[Any] = None,
) -> JSONResponse:
    """
    Constructs a standardized, user-friendly JSON error response.
    Guarantees no raw stack traces or SQL leaks to clients.
    """
    req_id = request_id or get_request_id()

    response_headers = {"X-Request-ID": req_id}
    if headers:
        response_headers.update(headers)

    body: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": req_id,
            "status_code": status_code,
        },
        # detail key maintained for 100% backward compatibility with FastAPI consumers
        "detail": message,
    }

    if extra_details is not None:
        body["error"]["details"] = extra_details

    return JSONResponse(
        status_code=status_code,
        content=body,
        headers=response_headers,
    )


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------


async def app_base_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    logger.warning(
        f"Handled application exception [{exc.code}]: {exc.message}",
        extra={
            "event": "app_exception",
            "error_code": exc.code,
            "status_code": exc.status_code,
            "request_id": get_request_id(),
        },
    )
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Intercepts SQLAlchemy errors (including OperationalError, DisconnectionError).
    Logs the full traceback internally while shielding client from internal schema/SQL leaks.
    """
    logger.error(
        f"Database operation failed: {str(exc)}",
        exc_info=True,
        extra={
            "event": "database_error",
            "error_type": type(exc).__name__,
            "request_id": get_request_id(),
        },
    )
    return create_error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="DATABASE_UNAVAILABLE",
        message="The database is currently unreachable. Please ensure the PostgreSQL container is running.",
    )


async def httpx_connect_exception_handler(request: Request, exc: httpx.ConnectError) -> JSONResponse:
    """
    Intercepts httpx.ConnectError (typically when connecting to local Ollama).
    """
    logger.error(
        f"Outbound connection failed: {str(exc)}",
        exc_info=True,
        extra={
            "event": "outbound_connect_error",
            "error_type": type(exc).__name__,
            "request_id": get_request_id(),
        },
    )
    return create_error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="OLLAMA_UNAVAILABLE",
        message="The local Ollama inference service is offline or unreachable on port 11434. Please ensure Ollama is running ('ollama serve').",
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Formats Pydantic request validation errors into a clean, human-readable summary.
    """
    errors = exc.errors()
    formatted_errors = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        formatted_errors.append(f"{loc}: {msg}" if loc else msg)

    summary_message = f"Validation failed: {'; '.join(formatted_errors)}"

    logger.info(
        f"Request validation failed: {summary_message}",
        extra={
            "event": "validation_error",
            "validation_errors": errors,
            "request_id": get_request_id(),
        },
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message=summary_message,
        extra_details=errors,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Maps standard FastAPI HTTPExceptions into the unified error envelope.
    """
    # Infer code from status code or detail
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "INFERENCE_FAILED",
        503: "SERVICE_UNAVAILABLE",
    }

    detail_str = str(exc.detail) if exc.detail else "An HTTP error occurred"
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

    # Refine not found if mentioning session
    if exc.status_code == 404 and "session" in detail_str.lower():
        code = "SESSION_NOT_FOUND"

    logger.warning(
        f"HTTPException [{code}] {exc.status_code}: {detail_str}",
        extra={
            "event": "http_exception",
            "status_code": exc.status_code,
            "error_code": code,
            "request_id": get_request_id(),
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        code=code,
        message=detail_str,
        headers=exc.headers,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches any unhandled unexpected exception.
    Guarantees internal stack trace is logged to server logs but NEVER leaked to client.
    """
    logger.exception(
        f"Unhandled server exception: {str(exc)}",
        extra={
            "event": "unhandled_exception",
            "error_type": type(exc).__name__,
            "request_id": get_request_id(),
        },
    )
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal error occurred. Please contact support or retry.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application."""
    app.add_exception_handler(AppBaseException, app_base_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(OperationalError, sqlalchemy_exception_handler)
    app.add_exception_handler(httpx.ConnectError, httpx_connect_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
