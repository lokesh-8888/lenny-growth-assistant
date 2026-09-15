"""
LLM Router with dynamic multi-provider routing and zero-downtime automatic fallback to local Ollama.
"""

import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm.base import BaseLLMProvider, LLMProviderError
from app.services.llm.catalog import (
    DEFAULT_MODEL_ID,
    get_all_models,
    get_model_metadata,
)
from app.services.llm.cloud_provider import (
    AnthropicProvider,
    CloudProvider,
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
)
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.types import ConfigResponse, LLMResponse

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Orchestrates LLM requests between local Ollama and Cloud providers.
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

        # Dedicated multi-provider adapters for explicit model routing
        self.gemini_provider = GeminiProvider()
        self.groq_provider = GroqProvider()
        self.openai_provider = OpenAIProvider()
        self.anthropic_provider = AnthropicProvider()

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
            available_providers=["ollama", "groq", "gemini", "anthropic", "openai"],
            cloud_configured=is_cloud_ready,
        )

    def _resolve_provider_for_model(self, model_id: str) -> Optional[BaseLLMProvider]:
        """Maps a model identifier (e.g. 'google:gemini-1.5-flash') to its provider instance."""
        if model_id.startswith("ollama:"):
            return self.ollama_provider
        if model_id.startswith("google:"):
            return self.gemini_provider
        if model_id.startswith("groq:"):
            return self.groq_provider
        if model_id.startswith("anthropic:"):
            return self.anthropic_provider
        if model_id.startswith("openai:"):
            return self.openai_provider
        return None

    async def complete(
        self,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """
        Executes completion with automatic fallback to Ollama if cloud provider fails.
        """
        # Case 1: Explicit model requested (dynamic multi-provider routing)
        if model:
            target_provider = self._resolve_provider_for_model(model)
            meta = get_model_metadata(model)

            # Local model requested (Ollama 3B or 8B)
            if target_provider == self.ollama_provider or (meta and meta.is_local):
                clean_tag = model.split("ollama:", 1)[-1] if "ollama:" in model else model
                resp = await self.ollama_provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=clean_tag,
                )
                resp.served_by = model
                return resp

            # Cloud model requested
            if target_provider:
                is_available = await target_provider.is_available()
                if not is_available:
                    logger.warning(
                        f"[LLMRouter] Cloud model '{model}' has no API key configured. "
                        f"Executing seamless zero-downtime fallback to local Ollama."
                    )
                    fallback_resp = await self.ollama_provider.complete(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    fallback_resp.served_by = f"ollama-fallback (requested: {model})"
                    return fallback_resp

                try:
                    resp = await target_provider.complete(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    resp.served_by = model
                    return resp
                except Exception as exc:
                    logger.warning(
                        f"[LLMRouter] Cloud model '{model}' call failed: {exc}. "
                        f"Executing seamless zero-downtime fallback to local Ollama."
                    )
                    fallback_resp = await self.ollama_provider.complete(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    fallback_resp.served_by = f"ollama-fallback (requested: {model})"
                    return fallback_resp

        # Case 2: Legacy fallback routing (via global primary_provider)
        if self._primary_provider_name == "cloud":
            try:
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
                fallback_resp = await self.ollama_provider.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                fallback_resp.served_by = "ollama-fallback"
                return fallback_resp

        # Case 3: Default Ollama dispatch
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
