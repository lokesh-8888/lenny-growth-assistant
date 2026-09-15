"""
Multi-component granular health check router.
"""

import time
from typing import List
from fastapi import APIRouter, Depends, Response, status
import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import (
    CloudLLMStatus,
    DependenciesStatus,
    HealthResponse,
    OllamaStatus,
    PostgresStatus,
)

router = APIRouter(tags=["Health"])


async def check_ollama(base_url: str) -> OllamaStatus:
    """Checks reachability of Ollama service and lists available models."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if "name" in m]
                return OllamaStatus(status="reachable", models_available=models)
            return OllamaStatus(
                status="unreachable",
                error=f"Unexpected status code {resp.status_code}",
            )
    except Exception as exc:
        return OllamaStatus(status="unreachable", error=str(exc))


def check_cloud_llm() -> CloudLLMStatus:
    """Checks if cloud LLM keys are configured across supported providers (without making network calls)."""
    providers_map = {
        "groq": bool(settings.groq_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "groq" else None)),
        "gemini": bool(settings.gemini_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "gemini" else None)),
        "anthropic": bool(settings.anthropic_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "anthropic" else None)),
        "openai": bool(settings.openai_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "openai" else None)),
    }
    configured = any(providers_map.values())
    primary_configured = None
    for p in ("groq", "gemini", "anthropic", "openai"):
        if providers_map[p]:
            primary_configured = p
            break
    return CloudLLMStatus(
        provider=primary_configured,
        configured=configured,
        providers=providers_map,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Multi-component granular health check",
)
async def get_health(response: Response, db: Session = Depends(get_db)):
    # 1. Postgres check
    start = time.perf_counter()
    try:
        db.execute(text("SELECT 1;"))
        latency = (time.perf_counter() - start) * 1000
        pg_status = PostgresStatus(status="connected", latency_ms=round(latency, 2))
    except Exception as exc:
        pg_status = PostgresStatus(status="disconnected", error=str(exc))

    # 2. Ollama check
    ollama_status = await check_ollama(settings.ollama_base_url)

    # 3. Cloud LLM config check
    cloud_status = check_cloud_llm()

    # Determine overall status
    if pg_status.status != "connected":
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif ollama_status.status != "reachable":
        overall_status = "degraded"
        response.status_code = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        response.status_code = status.HTTP_200_OK

    return HealthResponse(
        status=overall_status,
        dependencies=DependenciesStatus(
            postgres=pg_status,
            ollama=ollama_status,
            cloud_llm=cloud_status,
        ),
    )
