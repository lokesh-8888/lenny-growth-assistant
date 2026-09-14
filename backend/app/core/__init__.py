"""
Core module for logging, exceptions, and foundational utilities.
"""

from app.core.logging import (
    get_logger,
    get_request_id,
    get_session_id,
    request_id_ctx,
    session_id_ctx,
    set_request_id,
    set_session_id,
    setup_logging,
)
from app.core.exceptions import (
    AppBaseException,
    DatabaseUnavailableError,
    InferenceFailedError,
    OllamaUnavailableError,
    SessionNotFoundError,
    create_error_response,
    register_exception_handlers,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "get_request_id",
    "set_request_id",
    "get_session_id",
    "set_session_id",
    "request_id_ctx",
    "session_id_ctx",
    "AppBaseException",
    "DatabaseUnavailableError",
    "OllamaUnavailableError",
    "InferenceFailedError",
    "SessionNotFoundError",
    "create_error_response",
    "register_exception_handlers",
]
