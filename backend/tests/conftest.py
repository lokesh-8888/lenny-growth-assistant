"""
Pytest fixtures for backend API testing.
Standardizes test database connections, mock LLM clients, and sample test data.
"""

import os
import sys
from pathlib import Path
from typing import Generator, List
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import SessionModel, MessageModel, ChunkModel, ArtifactModel
from app.services.rag.types import Citation, RetrievedChunk


@pytest.fixture(scope="session")
def db_engine():
    """Ensure database schema is created on test database."""
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator:
    """Provides a transactional database session for each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with database session dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_session(db_session) -> Generator[SessionModel, None, None]:
    """Creates a temporary test session and cleans it up after test."""
    session_id = uuid.uuid4()
    sess = SessionModel(
        id=session_id,
        title="Test Growth Session",
        meta_info={"test": True},
    )
    db_session.add(sess)
    db_session.commit()
    db_session.refresh(sess)

    yield sess

    # Cleanup
    try:
        db_session.query(ArtifactModel).filter(ArtifactModel.session_id == session_id).delete()
        db_session.query(MessageModel).filter(MessageModel.session_id == session_id).delete()
        db_session.query(SessionModel).filter(SessionModel.id == session_id).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def sample_retrieved_chunks() -> List[RetrievedChunk]:
    """Provides standard retrieved chunks for RAG engine tests."""
    return [
        RetrievedChunk(
            id=uuid.uuid4(),
            content="According to Shreyas Doshi, high-agency product managers prioritize leverage and impact over task completion.",
            speaker="Shreyas Doshi",
            episode_title="Good Product Manager, Great Product Manager",
            guest_name="Shreyas Doshi",
            source_url="https://youtube.com/watch?v=shreyas123",
            start_timestamp="00:14:20",
            similarity_score=0.885,
        ),
        RetrievedChunk(
            id=uuid.uuid4(),
            content="Customer empathy involves feeling the user's pain, whereas customer obsession requires systematic product solutions.",
            speaker="Shreyas Doshi",
            episode_title="Good Product Manager, Great Product Manager",
            guest_name="Shreyas Doshi",
            source_url="https://youtube.com/watch?v=shreyas123",
            start_timestamp="00:22:15",
            similarity_score=0.842,
        ),
    ]


@pytest.fixture
def mock_ollama_embed():
    """Mocks QueryEmbedder returning a 768-dimensional normalized float vector."""
    mock = AsyncMock()
    mock.embed_query = AsyncMock(return_value=[0.05] * 768)
    return mock


@pytest.fixture
def mock_ollama_chat_response():
    """Generates standard Ollama LLM completion dictionary."""
    return {
        "content": "Grounded response based on operator interview transcripts.",
        "model": "llama3.1:8b",
        "provider": "ollama",
        "latency_ms": 150.0,
    }
