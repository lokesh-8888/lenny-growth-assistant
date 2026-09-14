"""
Pydantic schemas for request validation and response serialization.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Session Schemas
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255, description="Optional title for the session")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom session metadata")


class SessionResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Message Schemas
# ---------------------------------------------------------------------------

class MessageCreate(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Role of the message sender"
    )
    content: str = Field(..., min_length=1, description="Message text content")
    citations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional citation metadata"
    )
    served_by: Optional[str] = Field(
        default=None, description="Identifier of the LLM provider/model that served the message"
    )


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = None
    served_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Health Check Schemas
# ---------------------------------------------------------------------------

class PostgresStatus(BaseModel):
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class OllamaStatus(BaseModel):
    status: str
    models_available: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class CloudLLMStatus(BaseModel):
    provider: Optional[str] = None
    configured: bool = False


class DependenciesStatus(BaseModel):
    postgres: PostgresStatus
    ollama: OllamaStatus
    cloud_llm: CloudLLMStatus


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    dependencies: DependenciesStatus


class ErrorResponse(BaseModel):
    detail: str
