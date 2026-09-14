"""
LLM Services package exposing BaseLLMProvider, OllamaProvider, CloudProvider, and LLMRouter.
"""

from app.services.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.services.llm.cloud_provider import CloudProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.router import LLMRouter, get_llm_router
from app.services.llm.types import ChatMessage, ConfigResponse, LLMRequest, LLMResponse

__all__ = [
    "BaseLLMProvider",
    "ChatMessage",
    "CloudProvider",
    "ConfigResponse",
    "get_llm_router",
    "LLMAuthenticationError",
    "LLMConnectionError",
    "LLMProviderError",
    "LLMRateLimitError",
    "LLMRequest",
    "LLMResponse",
    "LLMRouter",
    "LLMTimeoutError",
    "OllamaProvider",
]
