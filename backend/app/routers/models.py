"""
Models API router exposing available local and cloud LLM models with live status.
"""

from typing import List
from fastapi import APIRouter, Depends

from app.services.llm.catalog import ModelMetadata, get_all_models
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.router import LLMRouter, get_llm_router

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get(
    "",
    response_model=List[ModelMetadata],
    summary="List supported LLM models with real-time provider availability status",
)
async def list_models(
    llm_router: LLMRouter = Depends(get_llm_router),
) -> List[ModelMetadata]:
    """
    Returns full list of catalog models with live availability checks:
    - Local models check if the Ollama daemon is reachable.
    - Cloud models check if their required API key environment variable is configured.
    """
    ollama_ok = await llm_router.ollama_provider.is_available()
    return get_all_models(ollama_available=ollama_ok)
