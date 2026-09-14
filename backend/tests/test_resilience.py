"""
Unit and integration tests for Phase 8: Observability, Request Tracing, and Outage Resilience.
"""

import json
import logging
from unittest.mock import AsyncMock, MagicMock
import uuid

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.core.logging import JSONLogFormatter, get_request_id, set_request_id
from app.database import get_db
from app.main import app
from app.services.rag.engine import get_rag_engine


# ---------------------------------------------------------------------------
# 1. Request ID & Tracing Tests
# ---------------------------------------------------------------------------


def test_request_id_generated_and_returned_in_headers(client):
    """Verify X-Request-ID and X-Response-Time-Ms are returned on all responses."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers

    # Validate that it is a valid UUID
    req_id = response.headers["x-request-id"]
    parsed_uuid = uuid.UUID(req_id)
    assert str(parsed_uuid) == req_id

    # Validate numeric response time
    elapsed = float(response.headers["x-response-time-ms"])
    assert elapsed >= 0.0


def test_request_id_incoming_header_preserved(client):
    """Verify an existing X-Request-ID supplied by client is preserved."""
    client_req_id = "client-trace-id-12345"
    response = client.get("/health", headers={"X-Request-ID": client_req_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == client_req_id


# ---------------------------------------------------------------------------
# 2. Database Disconnection & Resilience Tests
# ---------------------------------------------------------------------------


def test_db_connection_drop_returns_503_database_unavailable(client):
    """
    Simulate database connection failure (OperationalError) during session query.
    Verify clean HTTP 503 with code DATABASE_UNAVAILABLE and zero leaked tracebacks.
    """
    class BrokenDB:
        def query(self, *args, **kwargs):
            raise OperationalError("connection refused", {}, Exception("DB down"))

    app.dependency_overrides[get_db] = lambda: BrokenDB()

    try:
        response = client.get("/api/sessions")
        assert response.status_code == 503

        body = response.json()
        assert "error" in body
        err = body["error"]
        assert err["code"] == "DATABASE_UNAVAILABLE"
        assert "unreachable" in err["message"].lower()
        assert err["status_code"] == 503
        assert "request_id" in err
        assert response.headers["x-request-id"] == err["request_id"]

        # Verify backward compatibility detail
        assert "detail" in body

        # Verify zero tracebacks or internal SQL leaked
        raw_text = response.text
        assert "Traceback" not in raw_text
        assert "OperationalError" not in raw_text
        assert "connection refused" not in raw_text
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# 3. Ollama Service Unreachable Tests
# ---------------------------------------------------------------------------


def test_ollama_service_drop_returns_503_ollama_unavailable(client):
    """
    Simulate Ollama connection failure (ConnectError).
    Verify clean HTTP 503 with code OLLAMA_UNAVAILABLE.
    """
    mock_engine = MagicMock()
    req = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_engine.answer = AsyncMock(
        side_effect=httpx.ConnectError("Failed to connect to Ollama", request=req)
    )

    app.dependency_overrides[get_rag_engine] = lambda: mock_engine

    try:
        response = client.post("/api/chat", json={"message": "What are growth loops?"})
        assert response.status_code == 503

        body = response.json()
        assert "error" in body
        err = body["error"]
        assert err["code"] == "OLLAMA_UNAVAILABLE"
        assert "Ollama" in err["message"]
        assert err["status_code"] == 503
        assert "request_id" in err
        assert response.headers["x-request-id"] == err["request_id"]

        # Verify zero raw stack trace
        assert "Traceback" not in response.text
        assert "ConnectError" not in response.text
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)


# ---------------------------------------------------------------------------
# 4. Validation Error Envelope Tests
# ---------------------------------------------------------------------------


def test_validation_error_returns_clean_envelope(client):
    """
    Send invalid payload (empty message) to /api/chat.
    Verify HTTP 422 with VALIDATION_ERROR envelope.
    """
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422

    body = response.json()
    assert "error" in body
    err = body["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "Validation failed" in err["message"]
    assert err["status_code"] == 422
    assert "request_id" in err
    assert "detail" in body


# ---------------------------------------------------------------------------
# 5. Generic Unhandled Exception Tests
# ---------------------------------------------------------------------------


def test_generic_unhandled_exception_returns_500_with_zero_leaks(client):
    """
    Simulate unexpected internal error.
    Verify HTTP 500 with safe error envelope and NO raw stack trace.
    """
    class CrashingDB:
        def query(self, *args, **kwargs):
            raise RuntimeError("Critical secret internal key exposed: ABC123XYZ")

    app.dependency_overrides[get_db] = lambda: CrashingDB()

    try:
        response = client.get("/api/sessions")
        assert response.status_code == 500

        body = response.json()
        assert "error" in body
        err = body["error"]
        assert err["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected internal error" in err["message"].lower()
        assert err["status_code"] == 500
        assert response.headers["x-request-id"] == err["request_id"]

        # Absolute verification of zero leaks
        assert "Critical secret" not in response.text
        assert "ABC123XYZ" not in response.text
        assert "RuntimeError" not in response.text
        assert "Traceback" not in response.text
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# 6. Structured JSON Log Formatter Tests
# ---------------------------------------------------------------------------


def test_json_log_formatter_emits_valid_json_with_contextvars():
    """Verify JSONLogFormatter formats records as single-line JSON with contextvars."""
    formatter = JSONLogFormatter()
    logger = logging.getLogger("test.logger")

    test_req_id = "test-req-uuid-999"
    set_request_id(test_req_id)

    record = logger.makeRecord(
        name="app.services.rag.agent",
        level=logging.INFO,
        fn="agent.py",
        lno=42,
        msg="RAG completion finished (1162.5ms)",
        args=(),
        exc_info=None,
        extra={
            "event": "rag_completion_success",
            "provider": "ollama",
            "served_by": "ollama",
            "model": "llama3.1:8b",
            "retrieval_hits": 5,
            "top_similarity_score": 0.82,
            "retrieval_latency_ms": 42.1,
            "llm_latency_ms": 1120.4,
            "total_latency_ms": 1162.5,
        },
    )

    formatted_str = formatter.format(record)

    # Must be valid single-line JSON
    assert "\n" not in formatted_str
    parsed = json.loads(formatted_str)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "app.services.rag.agent"
    assert parsed["request_id"] == test_req_id
    assert parsed["event"] == "rag_completion_success"
    assert parsed["provider"] == "ollama"
    assert parsed["served_by"] == "ollama"
    assert parsed["model"] == "llama3.1:8b"
    assert parsed["retrieval_hits"] == 5
    assert parsed["top_similarity_score"] == 0.82
    assert parsed["retrieval_latency_ms"] == 42.1
    assert parsed["llm_latency_ms"] == 1120.4
    assert parsed["total_latency_ms"] == 1162.5
    assert "timestamp" in parsed
