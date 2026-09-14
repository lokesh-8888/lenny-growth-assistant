"""
LLM Router with zero-downtime automatic fallback to local Ollama.
"""

import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm.base import BaseLLMProvider, LLMProviderError
from app.services.llm.cloud_provider import CloudProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.types import ConfigResponse, LLMResponse

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Orchestrates LLM requests between local Ollama and Cloud providers (Groq/Gemini).
    Ensures zero downtime: any cloud provider failure seamlessly falls back to Ollama.
    """

    def __init__(
        self,
        primary_provider: Optional[str] = None,
        ollama_provider: Optional[BaseLLMProvider] = None,
        cloud_provider: Optional[BaseLLMProvider] = None,
    ):
        self._primary_provider_name = (
            primary_provider or settings.llm_provider
        ).lower()
        self.ollama_provider = ollama_provider or OllamaProvider()
        self.cloud_provider = cloud_provider or CloudProvider()

    @property
    def primary_provider(self) -> str:
        return self._primary_provider_name

    @property
    def active_provider(self) -> BaseLLMProvider:
        if self._primary_provider_name == "cloud":
            return self.cloud_provider
        return self.ollama_provider

    def get_config(self) -> ConfigResponse:
        """Returns the active LLM routing configuration and status."""
        current_model = (
            self.cloud_provider.model_name
            if self._primary_provider_name == "cloud"
            else self.ollama_provider.model_name
        )
        is_cloud_ready = bool(
            settings.resolved_cloud_api_key and settings.resolved_cloud_api_key.strip()
        )

        return ConfigResponse(
            current_provider=self._primary_provider_name,
            current_model=current_model,
            fallback_provider="ollama",
            fallback_model=self.ollama_provider.model_name,
            available_providers=["ollama", "groq", "gemini"],
            cloud_configured=is_cloud_ready,
        )

    async def complete(
        self,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """
        Executes completion with automatic fallback to Ollama if cloud provider fails.
        """
        if self._primary_provider_name == "cloud":
            try:
                # Check if key is present before attempting
                is_available = await self.cloud_provider.is_available()
                if not is_available:
                    raise LLMProviderError(
                        f"Cloud provider '{self.cloud_provider.provider_name}' has no API key configured."
                    )

                resp = await self.cloud_provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp
            except Exception as exc:
                logger.warning(
                    f"[LLMRouter] Cloud provider '{self.cloud_provider.provider_name}' failed: {exc}. "
                    f"Falling back transparently to Ollama ({self.ollama_provider.model_name})."
                )
                # Transparent fallback to Ollama
                fallback_resp = await self.ollama_provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                fallback_resp.served_by = "ollama-fallback"
                return fallback_resp

        # Default Ollama dispatch
        resp = await self.ollama_provider.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        resp.served_by = "ollama"
        return resp


_router_instance: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Dependency / accessor for the singleton LLMRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
