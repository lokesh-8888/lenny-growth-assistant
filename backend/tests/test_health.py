"""
Unit tests for multi-component /health endpoint.
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.schemas import OllamaStatus


def test_health_live_endpoint(client: TestClient):
    """Test health check against running services."""
    resp = client.get("/health")
    # Since Postgres is running, response code should be 200 (healthy or degraded)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "dependencies" in data
    assert data["dependencies"]["postgres"]["status"] == "connected"
    assert "latency_ms" in data["dependencies"]["postgres"]
    assert "ollama" in data["dependencies"]
    assert "cloud_llm" in data["dependencies"]


def test_health_ollama_unreachable(client: TestClient):
    """Test that when Ollama is unreachable, health status is 'degraded' with 200 OK."""
    with patch("app.routers.health.check_ollama", new_callable=AsyncMock) as mock_ollama:
        mock_ollama.return_value = OllamaStatus(
            status="unreachable",
            error="Connection refused to localhost:11434",
        )
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["ollama"]["status"] == "unreachable"
        assert data["dependencies"]["postgres"]["status"] == "connected"


def test_health_postgres_down(client: TestClient):
    """Test that when Postgres is down, health returns 503 with 'unhealthy' status."""
    class BrokenDB:
        def execute(self, *args, **kwargs):
            raise OperationalError("Connection terminated", {}, None)

    from app.database import get_db
    from app.main import app

    def override_broken_db():
        yield BrokenDB()

    app.dependency_overrides[get_db] = override_broken_db
    try:
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["dependencies"]["postgres"]["status"] == "disconnected"
    finally:
        app.dependency_overrides.clear()


def test_health_cloud_llm_configured():
    """Test cloud_llm reports configured true when API key is set."""
    from app.routers.health import check_cloud_llm
    with patch("app.routers.health.settings") as mock_settings:
        mock_settings.groq_api_key = "gsk_test_key_12345"
        mock_settings.gemini_api_key = None
        status = check_cloud_llm()
        assert status.configured is True
        assert status.provider == "groq"
