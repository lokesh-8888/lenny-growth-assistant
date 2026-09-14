"""
Cloud LLM Provider targeting OpenAI-compatible free tiers (Groq and Google Gemini).
"""

import time
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.services.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.services.llm.types import LLMResponse


DEFAULT_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}

DEFAULT_PROVIDER_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-1.5-flash",
}


class CloudProvider(BaseLLMProvider):
    """
    Client for OpenAI-compatible free cloud LLM endpoints (Groq / Gemini).
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.provider = (provider or settings.cloud_llm_provider).lower()
        self.api_key = api_key or settings.resolved_cloud_api_key
        self.model = model or settings.cloud_llm_model or DEFAULT_PROVIDER_MODELS.get(self.provider, "llama-3.3-70b-versatile")
        self.base_url = (
            base_url
            or settings.cloud_llm_base_url
            or DEFAULT_PROVIDER_BASE_URLS.get(self.provider, "https://api.groq.com/openai/v1")
        ).rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return self.provider

    @property
    def model_name(self) -> str:
        return self.model

    async def is_available(self) -> bool:
        """Returns True if an API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    async def complete(
        self,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """
        Executes chat completion against OpenAI-compatible endpoint.
        """
        if not self.api_key or not self.api_key.strip():
            raise LLMAuthenticationError(
                f"Cloud provider '{self.provider}' has no API key configured."
            )

        chat_messages: List[Dict[str, str]] = []
        if messages:
            chat_messages = list(messages)
            if system_prompt and not any(m.get("role") == "system" for m in chat_messages):
                chat_messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            chat_messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        endpoint = f"{self.base_url}/chat/completions"
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code == 401 or resp.status_code == 403:
                    raise LLMAuthenticationError(
                        f"Cloud provider authentication failed (HTTP {resp.status_code}): {resp.text}"
                    )
                if resp.status_code == 429:
                    raise LLMRateLimitError(
                        f"Cloud provider rate limit encountered (HTTP 429): {resp.text}"
                    )
                if resp.status_code != 200:
                    raise LLMProviderError(
                        f"Cloud provider error (HTTP {resp.status_code}): {resp.text}"
                    )
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Cloud provider timeout after {self.timeout}s: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMConnectionError(f"Connection to cloud provider failed: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(f"Unexpected cloud provider error: {exc}") from exc

        duration_ms = (time.perf_counter() - start_time) * 1000

        choices = data.get("choices", [])
        if not choices:
            raise LLMProviderError(f"Malformed response from cloud provider: {data}")

        content = choices[0].get("message", {}).get("content", "")
        usage_data = data.get("usage", {})
        usage = {
            "prompt_tokens": usage_data.get("prompt_tokens", 0),
            "completion_tokens": usage_data.get("completion_tokens", 0),
            "total_tokens": usage_data.get("total_tokens", 0),
        }

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            served_by=self.provider,
            latency_ms=round(duration_ms, 2),
            usage=usage,
        )
