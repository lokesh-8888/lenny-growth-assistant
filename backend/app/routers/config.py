"""
Configuration introspection router exposing active LLM models and fallback status.
"""

from fastapi import APIRouter, Depends
from app.services.llm.router import LLMRouter, get_llm_router
from app.services.llm.types import ConfigResponse

router = APIRouter(prefix="/api/config", tags=["Configuration"])


@router.get(
    "",
    response_model=ConfigResponse,
    summary="Get active LLM routing configuration and provider status",
)
def get_config(llm_router: LLMRouter = Depends(get_llm_router)):
    return llm_router.get_config()
