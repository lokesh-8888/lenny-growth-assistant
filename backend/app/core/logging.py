"""
Structured JSON logging module with contextvars request tracing.
Zero external dependencies, 100% standard library.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any, Dict, Optional

# Context variables for tracing across async execution frames
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="")
session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id_ctx", default=None)


def get_request_id() -> str:
    """Retrieve the current request ID from contextvars."""
    return request_id_ctx.get() or ""


def set_request_id(req_id: str) -> Any:
    """Set the current request ID in contextvars."""
    return request_id_ctx.set(req_id)


def get_session_id() -> Optional[str]:
    """Retrieve the current session ID from contextvars."""
    return session_id_ctx.get()


def set_session_id(sess_id: Optional[str]) -> Any:
    """Set the current session ID in contextvars."""
    return session_id_ctx.set(sess_id)


STANDARD_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "taskName",
}


class JSONLogFormatter(logging.Formatter):
    """
    Emits single-line structured JSON logs to stdout.
    Automatically merges contextvars (request_id, session_id) and custom extra attributes.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base structured fields
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject contextvars or record overrides
        req_id = getattr(record, "request_id", None) or get_request_id()
        if req_id:
            log_obj["request_id"] = req_id

        sess_id = getattr(record, "session_id", None) or get_session_id()
        if sess_id:
            log_obj["session_id"] = sess_id

        # Merge extra fields passed to logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in STANDARD_RECORD_ATTRS and key not in log_obj:
                log_obj[key] = value

        # If an event field is present in extra, promote/prioritize it
        if "event" in record.__dict__:
            log_obj["event"] = record.__dict__["event"]

        # Capture exception tracebacks inside backend logs without leaking to users
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                log_obj["exception"] = record.exc_text

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """
    Configures the root logger with the appropriate formatter and log level.
    """
    from app.config import settings

    level_str = (log_level or settings.log_level).upper()
    format_str = (log_format or settings.log_format).lower()

    level = getattr(logging, level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if format_str == "json":
        handler.setFormatter(JSONLogFormatter())
    else:
        text_fmt = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
        handler.setFormatter(logging.Formatter(text_fmt))

    root_logger.addHandler(handler)

    # Align uvicorn and sqlalchemy loggers
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with the given module name."""
    return logging.getLogger(name)
