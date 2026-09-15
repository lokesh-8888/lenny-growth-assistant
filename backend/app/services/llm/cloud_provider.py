"""
Cloud LLM Provider adapters for Google Gemini, Groq, OpenAI, and Anthropic.
Implements standardized OpenAI-compatible and Anthropic REST interfaces.
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


class BaseOpenAICompatibleProvider(BaseLLMProvider):
    """
    Base client for OpenAI-compatible chat completion endpoints.
    Used by Groq, Google Gemini, and OpenAI.
    """

    def __init__(
        self,
        provider_name: str,
        api_key: Optional[str] = None,
        model: str = "",
        base_url: str = "",
        timeout: float = 30.0,
    ):
        self._provider_name = provider_name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self.model

    async def is_available(self) -> bool:
        """Returns True if a valid API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    async def complete(
        self,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        if not self.api_key or not self.api_key.strip():
            raise LLMAuthenticationError(
                f"Cloud provider '{self.provider_name}' has no API key configured."
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
                if resp.status_code in (401, 403):
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
            provider=self.provider_name,
            served_by=self.provider_name,
            latency_ms=round(duration_ms, 2),
            usage=usage,
        )


class GroqProvider(BaseOpenAICompatibleProvider):
    """Client for Groq OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 30.0,
    ):
        resolved_key = (
            api_key
            or settings.groq_api_key
            or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "groq" else None)
        )
        super().__init__(
            provider_name="groq",
            api_key=resolved_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )


class GeminiProvider(BaseOpenAICompatibleProvider):
    """Client for Google Gemini OpenAI-compatible REST endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        timeout: float = 30.0,
    ):
        resolved_key = (
            api_key
            or settings.gemini_api_key
            or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "gemini" else None)
        )
        super().__init__(
            provider_name="google",
            api_key=resolved_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )


class OpenAIProvider(BaseOpenAICompatibleProvider):
    """Client for official OpenAI endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ):
        resolved_key = (
            api_key
            or settings.openai_api_key
            or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "openai" else None)
        )
        super().__init__(
            provider_name="openai",
            api_key=resolved_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )


class AnthropicProvider(BaseLLMProvider):
    """Client for Anthropic Claude Messages API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 45.0,
    ):
        self._provider_name = "anthropic"
        self.api_key = (
            api_key
            or settings.anthropic_api_key
            or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "anthropic" else None)
        )
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self.model

    async def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def complete(
        self,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        if not self.api_key or not self.api_key.strip():
            raise LLMAuthenticationError("Anthropic provider has no API key configured.")

        # Extract system prompt if present in messages
        anthropic_system = system_prompt or ""
        anthropic_messages: List[Dict[str, str]] = []

        if messages:
            for m in messages:
                if m.get("role") == "system":
                    anthropic_system = (anthropic_system + "\n" + m.get("content", "")).strip()
                else:
                    anthropic_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        else:
            anthropic_messages.append({"role": "user", "content": prompt})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if anthropic_system:
            payload["system"] = anthropic_system

        endpoint = f"{self.base_url}/messages"
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                if resp.status_code in (401, 403):
                    raise LLMAuthenticationError(
                        f"Anthropic authentication failed (HTTP {resp.status_code}): {resp.text}"
                    )
                if resp.status_code == 429:
                    raise LLMRateLimitError(
                        f"Anthropic rate limit encountered (HTTP 429): {resp.text}"
                    )
                if resp.status_code != 200:
                    raise LLMProviderError(
                        f"Anthropic error (HTTP {resp.status_code}): {resp.text}"
                    )
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Anthropic timeout after {self.timeout}s: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMConnectionError(f"Connection to Anthropic failed: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(f"Unexpected Anthropic error: {exc}") from exc

        duration_ms = (time.perf_counter() - start_time) * 1000

        content_blocks = data.get("content", [])
        text_content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )
        usage_data = data.get("usage", {})
        usage = {
            "prompt_tokens": usage_data.get("input_tokens", 0),
            "completion_tokens": usage_data.get("output_tokens", 0),
            "total_tokens": usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
        }

        return LLMResponse(
            content=text_content,
            model=self.model,
            provider="anthropic",
            served_by="anthropic",
            latency_ms=round(duration_ms, 2),
            usage=usage,
        )


# Backward compatibility wrapper for existing code and tests
class CloudProvider(BaseOpenAICompatibleProvider):
    """
    Backward-compatible client matching the original CloudProvider constructor.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        chosen_provider = (provider or settings.cloud_llm_provider).lower()
        resolved_key = api_key or settings.resolved_cloud_api_key

        default_base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
            "openai": "https://api.openai.com/v1",
        }
        default_models = {
            "groq": "llama-3.3-70b-versatile",
            "gemini": "gemini-1.5-flash",
            "openai": "gpt-4o-mini",
        }

        resolved_model = model or settings.cloud_llm_model or default_models.get(chosen_provider, "llama-3.3-70b-versatile")
        resolved_base_url = (
            base_url
            or settings.cloud_llm_base_url
            or default_base_urls.get(chosen_provider, "https://api.groq.com/openai/v1")
        )

        super().__init__(
            provider_name=chosen_provider,
            api_key=resolved_key,
            model=resolved_model,
            base_url=resolved_base_url,
            timeout=timeout,
        )
