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
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")

    model_config = ConfigDict(from_attributes=True)


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


# ---------------------------------------------------------------------------
# Artifact Schemas (Phase 5 & 6)
# ---------------------------------------------------------------------------

class ArtifactGenerateRequest(BaseModel):
    session_id: UUID = Field(..., description="Active session ID providing conversation context")
    type: str = Field(default="ship30", description="Artifact type: ship30, markdown, html")
    title: Optional[str] = Field(default=None, max_length=255, description="Optional custom title")
    source_message_id: Optional[UUID] = Field(
        default=None, description="Optional specific message UUID to ground the artifact upon"
    )
    model: Optional[str] = Field(
        default=None,
        description="Requested model identifier, e.g. 'anthropic:claude-3-5-sonnet', 'ollama:llama3.2:3b'",
    )


class StructureValidation(BaseModel):
    is_valid: bool = Field(..., description="Whether output meets structural and length criteria")
    word_count: int = Field(..., description="Actual word count of generated content")
    target_word_count: int = Field(default=1250, description="Target word count")
    has_hook: bool = Field(default=True, description="Strong opening hook without throat-clearing")
    has_headings: bool = Field(default=True, description="Contains markdown ## or ### headings")
    has_bullets: bool = Field(default=True, description="Contains structured bullet or numbered list")
    has_bold: bool = Field(default=True, description="Contains bold text for visual skimming")
    has_takeaway: bool = Field(default=True, description="Contains dedicated takeaway section")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite structural score")
    issues: List[str] = Field(default_factory=list, description="Any detected structural issues")


class ArtifactResponse(BaseModel):
    id: UUID
    session_id: Optional[UUID] = None
    type: str
    title: str
    content: str
    word_count: int
    validation: Optional[StructureValidation] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    served_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactListItem(BaseModel):
    id: UUID
    session_id: Optional[UUID] = None
    type: str
    title: str
    word_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
