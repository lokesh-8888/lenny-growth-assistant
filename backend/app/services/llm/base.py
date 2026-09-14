"""
Abstract Base Class and exceptions for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.services.llm.types import LLMResponse


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication fails (missing or invalid API key)."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when provider rate limits (HTTP 429) are encountered."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when a generation request times out."""
    pass


class LLMConnectionError(LLMProviderError):
    """Raised when network connection to the provider fails."""
    pass


class BaseLLMProvider(ABC):
    """Abstract Base Class defining the standard LLM provider interface."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier name of this provider (e.g. 'ollama', 'groq', 'gemini')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the model identifier currently in use."""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """
        Generates a text completion given either a prompt or a sequence of messages.
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Checks if the provider is currently configured and reachable.
        """
        pass
