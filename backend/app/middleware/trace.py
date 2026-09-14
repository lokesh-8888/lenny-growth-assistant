"""
Request Tracing Middleware assigning and propagating X-Request-ID across contextvars and response headers.
"""

import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx

logger = get_logger("app.middleware.trace")


class TraceMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Extracts or generates a UUID request_id.
    2. Sets request_id in contextvars for downstream logging.
    3. Adds X-Request-ID and X-Response-Time-Ms to response headers.
    4. Logs structured request start and completion.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract existing X-Request-ID from incoming request headers or generate a new UUID
        incoming_req_id = request.headers.get("X-Request-ID")
        if incoming_req_id and len(incoming_req_id.strip()) > 0:
            req_id = incoming_req_id.strip()
        else:
            req_id = str(uuid.uuid4())

        # Bind to contextvar
        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Attach headers to response
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

            # Emit structured request completion log
            logger.info(
                f"{request.method} {request.url.path} {response.status_code} ({elapsed_ms}ms)",
                extra={
                    "event": "http_request_finished",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code,
                    "duration_ms": elapsed_ms,
                    "request_id": req_id,
                },
            )

            return response
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                f"{request.method} {request.url.path} failed with exception: {str(exc)}",
                extra={
                    "event": "http_request_exception",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "duration_ms": elapsed_ms,
                    "request_id": req_id,
                    "error_type": type(exc).__name__,
                },
            )

            # Enforce zero raw stack trace leakage
            from app.core.exceptions import (
                AppBaseException,
                create_error_response,
            )
            from sqlalchemy.exc import SQLAlchemyError
            import httpx

            if isinstance(exc, SQLAlchemyError):
                return create_error_response(
                    status_code=503,
                    code="DATABASE_UNAVAILABLE",
                    message="The database is currently unreachable. Please ensure the PostgreSQL container is running.",
                    request_id=req_id,
                )

            if isinstance(exc, httpx.ConnectError):
                return create_error_response(
                    status_code=503,
                    code="OLLAMA_UNAVAILABLE",
                    message="The local Ollama inference service is offline or unreachable on port 11434. Please ensure Ollama is running ('ollama serve').",
                    request_id=req_id,
                )

            if isinstance(exc, AppBaseException):
                return create_error_response(
                    status_code=exc.status_code,
                    code=exc.code,
                    message=exc.message,
                    request_id=req_id,
                )

            return create_error_response(
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal error occurred. Please contact support or retry.",
                request_id=req_id,
            )
        finally:
            request_id_ctx.reset(token)
