"""
SQLAlchemy ORM models for The Lenny Growth Assistant.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
    )
    # JSON column for extensible session metadata
    metadata_ = Column("metadata", JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)

    # Relationships
    messages = relationship(
        "MessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at.asc()",
    )
    artifacts = relationship(
        "ArtifactModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ArtifactModel.created_at.desc()",
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    citations = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True, default=list)
    served_by = Column(String(255), nullable=True)  # e.g., 'ollama', 'groq', 'ollama-fallback (requested: ...)'
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationship
    session = relationship("SessionModel", back_populates="messages")


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type = Column(String(50), nullable=False)  # 'ship30', 'markdown', 'html'
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationship
    session = relationship("SessionModel", back_populates="artifacts")


class ChunkModel(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)
    episode_title = Column(Text, nullable=True)
    guest = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)


class ProcessedFileModel(Base):
    __tablename__ = "processed_files"

    file_path = Column(Text, primary_key=True)
    file_hash = Column(String(64), nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
