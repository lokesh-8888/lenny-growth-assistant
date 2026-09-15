"""
Unit tests for the Unified Model Registry, GET /api/models endpoint,
dynamic multi-provider routing, and zero-downtime Ollama fallback.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.llm.base import LLMRateLimitError, LLMTimeoutError
from app.services.llm.catalog import MODEL_CATALOG, get_all_models, get_model_metadata
from app.services.llm.router import LLMRouter, get_llm_router
from app.services.llm.types import LLMResponse


@pytest.fixture
def test_client():
    return TestClient(app)


def test_get_models_catalog_endpoint(test_client):
    """Test GET /api/models returns 6 supported models with metadata and availability."""
    resp = test_client.get("/api/models")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6

    model_ids = [m["id"] for m in data]
    assert "ollama:llama3.2:3b" in model_ids
    assert "ollama:llama3.1:8b" in model_ids
    assert "google:gemini-1.5-flash" in model_ids
    assert "groq:llama-3.3-70b-versatile" in model_ids
    assert "anthropic:claude-3-5-sonnet" in model_ids
    assert "openai:gpt-4o-mini" in model_ids

    # Verify structured fields
    for item in data:
        assert "id" in item
        assert "name" in item
        assert "provider" in item
        assert "tier" in item
        assert "badge" in item
        assert "description" in item
        assert "context_window" in item
        assert "is_local" in item
        assert "is_available" in item
        assert isinstance(item["is_available"], bool)


def test_catalog_metadata_lookup():
    """Test model metadata lookup function."""
    m_3b = get_model_metadata("ollama:llama3.2:3b")
    assert m_3b is not None
    assert m_3b.name == "Llama 3.2 (3B)"
    assert m_3b.badge == "Fast"
    assert m_3b.is_local is True

    m_claude = get_model_metadata("anthropic:claude-3-5-sonnet")
    assert m_claude is not None
    assert m_claude.tier == "API Key"
    assert m_claude.badge == "Reasoning"
    assert m_claude.env_key == "ANTHROPIC_API_KEY"


@pytest.mark.asyncio
async def test_router_dynamic_ollama_8b_dispatch():
    """Test LLMRouter dynamically dispatches to Ollama 8B when requested."""
    mock_ollama = AsyncMock()
    mock_ollama.complete.return_value = LLMResponse(
        content="Grounded answer from 8B model.",
        model="llama3.1:8b",
        provider="ollama",
        served_by="ollama",
        latency_ms=120.0,
    )

    router = LLMRouter(ollama_provider=mock_ollama)
    resp = await router.complete(prompt="What is PMF?", model="ollama:llama3.1:8b")

    assert resp.content == "Grounded answer from 8B model."
    assert resp.served_by == "ollama:llama3.1:8b"
    mock_ollama.complete.assert_called_once()
    _, kwargs = mock_ollama.complete.call_args
    assert kwargs.get("model") == "llama3.1:8b"


@pytest.mark.asyncio
async def test_router_unconfigured_cloud_model_fallback():
    """
    NON-NEGOTIABLE REQUIREMENT:
    Selecting an unconfigured cloud model (missing API key) must NEVER fail.
    It must automatically route through local Ollama and tag response as
    'served_by': 'ollama-fallback (requested: <model_name>)'.
    """
    mock_ollama = AsyncMock()
    mock_ollama.complete.return_value = LLMResponse(
        content="Answer generated via local Ollama fallback.",
        model="llama3.2:3b",
        provider="ollama",
        served_by="ollama",
        latency_ms=100.0,
    )

    router = LLMRouter(ollama_provider=mock_ollama)
    # Ensure anthropic provider reports unavailable (no key)
    router.anthropic_provider.is_available = AsyncMock(return_value=False)

    resp = await router.complete(
        prompt="Explain growth loops.",
        model="anthropic:claude-3-5-sonnet",
    )

    assert resp.content == "Answer generated via local Ollama fallback."
    assert resp.served_by == "ollama-fallback (requested: anthropic:claude-3-5-sonnet)"
    mock_ollama.complete.assert_called_once()


@pytest.mark.asyncio
async def test_router_cloud_rate_limit_fallback():
    """
    NON-NEGOTIABLE REQUIREMENT:
    When a configured cloud model encounters 429 rate limit or timeout,
    it must automatically fall back to Ollama with the requested model tag.
    """
    mock_ollama = AsyncMock()
    mock_ollama.complete.return_value = LLMResponse(
        content="Resilient fallback answer from Ollama.",
        model="llama3.2:3b",
        provider="ollama",
        served_by="ollama",
        latency_ms=90.0,
    )

    router = LLMRouter(ollama_provider=mock_ollama)
    router.groq_provider.is_available = AsyncMock(return_value=True)
    router.groq_provider.complete = AsyncMock(side_effect=LLMRateLimitError("HTTP 429 Rate Limit Exceeded"))

    resp = await router.complete(
        prompt="Explain retention cohorts.",
        model="groq:llama-3.3-70b-versatile",
    )

    assert resp.content == "Resilient fallback answer from Ollama."
    assert resp.served_by == "ollama-fallback (requested: groq:llama-3.3-70b-versatile)"
    mock_ollama.complete.assert_called_once()


def test_chat_endpoint_with_model_param_and_fallback(test_client):
    """Test POST /api/chat with model param routes or falls back cleanly."""
    # Mock RAG agent retrieval to return grounded content
    mock_llm_resp = LLMResponse(
        content="Elena Verna explains that B2B product-led sales bridges self-serve and enterprise.",
        model="llama3.2:3b",
        provider="ollama",
        served_by="ollama-fallback (requested: anthropic:claude-3-5-sonnet)",
        latency_ms=150.0,
    )

    with patch("app.services.rag.agent.LLMRouter.complete", new_callable=AsyncMock, return_value=mock_llm_resp):
        payload = {
            "message": "How does product-led sales work according to Elena Verna?",
            "model": "anthropic:claude-3-5-sonnet",
        }
        resp = test_client.post("/api/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "Elena Verna" in data["content"]
        assert data["served_by"] == "ollama-fallback (requested: anthropic:claude-3-5-sonnet)"
