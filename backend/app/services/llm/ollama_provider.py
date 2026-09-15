"""
Ollama Local LLM Provider implementation.
"""

import time
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings
from app.services.llm.base import (
    BaseLLMProvider,
    LLMConnectionError,
    LLMProviderError,
    LLMTimeoutError,
)
from app.services.llm.types import LLMResponse


class OllamaProvider(BaseLLMProvider):
    """
    Interacts with the local Ollama daemon via HTTP REST API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout if timeout is not None else settings.ollama_timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self.model

    async def is_available(self) -> bool:
        """Checks if the local Ollama instance is responsive."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

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
        Executes chat completion against Ollama /api/chat.
        """
        target_model = model or self.model
        # Normalize ollama: prefix if provided (e.g. ollama:llama3.2:3b -> llama3.2:3b)
        if target_model.startswith("ollama:"):
            target_model = target_model.split("ollama:", 1)[1]

        # Prepare message history
        chat_messages: List[Dict[str, str]] = []
        if messages:
            chat_messages = list(messages)
            if system_prompt and not any(m.get("role") == "system" for m in chat_messages):
                chat_messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            if system_prompt:
                chat_messages.append({"role": "system", "content": system_prompt})
            chat_messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": chat_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        endpoint = f"{self.base_url}/api/chat"
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 404 and target_model != "llama3.1:8b":
                    # If target model (e.g. llama3.2:3b) not pulled, try llama3.1:8b as fallback
                    payload["model"] = "llama3.1:8b"
                    resp = await client.post(endpoint, json=payload)
                    if resp.status_code == 200:
                        target_model = "llama3.1:8b"
                if resp.status_code != 200:
                    raise LLMProviderError(
                        f"Ollama returned HTTP {resp.status_code}: {resp.text}"
                    )
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Ollama request timed out after {self.timeout}s: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMConnectionError(f"Failed to connect to Ollama at {self.base_url}: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(f"Unexpected Ollama error: {exc}") from exc

        duration_ms = (time.perf_counter() - start_time) * 1000

        content = data.get("message", {}).get("content", "")
        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        return LLMResponse(
            content=content,
            model=target_model,
            provider="ollama",
            served_by="ollama",
            latency_ms=round(duration_ms, 2),
            usage=usage,
        )
