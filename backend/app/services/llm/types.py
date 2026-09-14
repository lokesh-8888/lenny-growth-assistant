"""
Type definitions and Pydantic models for the LLM service layer.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class LLMRequest(BaseModel):
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1500, gt=0)


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    served_by: str  # e.g., "ollama", "groq", "gemini", "ollama-fallback"
    latency_ms: float
    usage: Optional[Dict[str, int]] = None


class ConfigResponse(BaseModel):
    current_provider: str
    current_model: str
    fallback_provider: str
    fallback_model: str
    available_providers: List[str]
    cloud_configured: bool
