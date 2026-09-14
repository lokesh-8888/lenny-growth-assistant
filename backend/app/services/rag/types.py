"""
Type definitions and Pydantic schemas for the RAG service layer.
"""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    id: int
    content: str
    episode_title: Optional[str] = None
    guest: Optional[str] = None
    source_url: Optional[str] = None
    content_hash: Optional[str] = None
    similarity: float = 0.0
    distance: float = 1.0

    @property
    def similarity_score(self) -> float:
        return self.similarity


class Citation(BaseModel):
    episode_title: str
    guest: Optional[str] = "Unknown"
    source_url: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[UUID] = Field(
        default=None,
        description="Optional session UUID. If omitted, a new session is created.",
    )
    message: str = Field(..., min_length=1, description="User question or prompt")
    stream: bool = Field(default=False, description="Streaming toggle (reserved for Phase 7)")
    temperature: Optional[float] = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )


class ChatResponse(BaseModel):
    session_id: UUID
    message_id: UUID
    role: str = "assistant"
    content: str
    citations: List[Citation] = Field(default_factory=list)
    served_by: str
    latency_ms: Optional[float] = None
    is_grounded: bool = True
