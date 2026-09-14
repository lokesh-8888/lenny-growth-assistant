"""
Tests for RAG services: QueryEmbedder, Retriever, Prompts, RAGEngine, and POST /api/chat endpoint.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ChunkModel, MessageModel, SessionModel
from app.services.rag.embedder import QueryEmbedder
from app.services.rag.engine import RAGEngine, get_rag_engine
from app.services.rag.prompts import (
    GROUNDED_SYSTEM_PROMPT,
    build_rag_messages,
    build_strict_refusal_response,
    format_context_chunks,
)
from app.services.rag.retriever import Retriever, extract_keywords
from app.services.rag.types import Citation, RetrievedChunk


# ---------------------------------------------------------------------------
# Unit Tests: QueryEmbedder
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_embedder_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={"embedding": [0.1] * 768})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        embedder = QueryEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        embedding = await embedder.embed_query("growth tactics")

        assert len(embedding) == 768
        assert embedding[0] == 0.1
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_embedder_failure():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Ollama connection error")
        embedder = QueryEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        with pytest.raises(Exception):
            await embedder.embed_query("growth tactics")


def test_extract_keywords():
    keywords = extract_keywords("What did Dan Hockenmaier say about marketplaces?")
    assert "dan" in keywords
    assert "hockenmaier" in keywords
    assert "marketplaces" in keywords
    assert "what" not in keywords
    assert "about" not in keywords


# ---------------------------------------------------------------------------
# Unit Tests: Prompts
# ---------------------------------------------------------------------------
def test_format_context_chunks():
    chunks = [
        RetrievedChunk(
            id=1,
            content="Willingness to pay dictates product features.",
            episode_title="How to Price Your SaaS",
            guest="Madhavan Ramanujam",
            source_url="https://youtube.com/watch?v=123",
            similarity=0.88,
        )
    ]
    formatted = format_context_chunks(chunks)
    assert "--- Excerpt 1" in formatted
    assert "Episode: \"How to Price Your SaaS\"" in formatted
    assert "Guest: Madhavan Ramanujam" in formatted
    assert "Willingness to pay dictates product features." in formatted


def test_build_rag_messages_with_history():
    chunks = [
        RetrievedChunk(
            id=1,
            content="Price early and often.",
            episode_title="How to Price Your SaaS",
            guest="Madhavan Ramanujam",
            source_url=None,
            similarity=0.85,
        )
    ]
    history = [
        MessageModel(session_id=uuid.uuid4(), role="user", content="Hi Lenny"),
        MessageModel(session_id=uuid.uuid4(), role="assistant", content="Hello! How can I help with growth?"),
    ]

    messages = build_rag_messages(
        user_query="What did Madhavan say about pricing?",
        chunks=chunks,
        conversation_history=history,
    )

    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hi Lenny"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert "What did Madhavan say about pricing?" in messages[3]["content"]


def test_build_strict_refusal_response():
    refusal = build_strict_refusal_response("quantum computing algorithms")
    assert "I couldn't find any discussion on 'quantum computing algorithms'" in refusal
    assert "Lenny's podcast transcripts archive" in refusal


# ---------------------------------------------------------------------------
# Unit Tests: RAGEngine
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rag_engine_strict_refusal_when_no_chunks():
    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])  # No relevant chunks
    mock_router = AsyncMock()

    engine = RAGEngine(
        retriever=mock_retriever,
        llm_router=mock_router,
    )

    result = await engine.answer(
        query="How do rockets reach orbit?",
        db=MagicMock(),
        conversation_history=[],
    )

    assert result["is_grounded"] is False
    assert len(result["citations"]) == 0
    assert result["served_by"] == "system-groundedness"
    assert "How do rockets reach orbit?" in result["content"]
    # Verify LLM was NOT called when guardrail triggered
    mock_router.complete.assert_not_called()


@pytest.mark.asyncio
async def test_rag_engine_grounded_answer():
    chunk = RetrievedChunk(
        id=1,
        content="Retention is the single most important growth metric.",
        episode_title="Retention Strategies",
        guest="Casey Winters",
        source_url="https://youtube.com/watch?v=casey",
        similarity=0.82,
    )
    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[chunk])

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Casey Winters explains that retention is the most critical metric for long-term growth."
    mock_llm_response.served_by = "ollama"

    mock_router = AsyncMock()
    mock_router.complete = AsyncMock(return_value=mock_llm_response)

    engine = RAGEngine(
        retriever=mock_retriever,
        llm_router=mock_router,
    )

    result = await engine.answer(
        query="Why is retention important?",
        db=MagicMock(),
        conversation_history=[],
    )

    assert result["is_grounded"] is True
    assert len(result["citations"]) == 1
    assert result["citations"][0].guest == "Casey Winters"
    assert result["citations"][0].episode_title == "Retention Strategies"
    assert result["citations"][0].source_url == "https://youtube.com/watch?v=casey"
    assert result["served_by"] == "ollama"
    assert "Casey Winters" in result["content"]
    mock_router.complete.assert_called_once()


# ---------------------------------------------------------------------------
# Integration Tests: POST /api/chat
# ---------------------------------------------------------------------------
def test_chat_creates_new_session_and_persists(client: TestClient, db_session):
    mock_rag = AsyncMock()
    mock_rag.answer = AsyncMock(return_value={
        "content": "Dan Hockenmaier emphasizes that marketplace liquidity is essential before scaling.",
        "citations": [
            Citation(
                episode_title="Marketplaces and Networks",
                guest="Dan Hockenmaier",
                source_url="https://youtube.com/watch?dan",
            )
        ],
        "served_by": "ollama",
        "is_grounded": True,
    })

    app.dependency_overrides[get_rag_engine] = lambda: mock_rag
    try:
        response = client.post(
            "/api/chat",
            json={"message": "What did Dan Hockenmaier say about marketplace liquidity?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message_id" in data
        assert data["is_grounded"] is True
        assert data["served_by"] == "ollama"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["guest"] == "Dan Hockenmaier"

        # Verify persisted in database
        sess = db_session.query(SessionModel).filter(SessionModel.id == data["session_id"]).first()
        assert sess is not None
        assert "What did Dan Hockenmaier say" in sess.title

        messages = (
            db_session.query(MessageModel)
            .filter(MessageModel.session_id == sess.id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "What did Dan Hockenmaier say about marketplace liquidity?"
        assert messages[1].role == "assistant"
        assert "Dan Hockenmaier emphasizes" in messages[1].content
        assert messages[1].citations is not None

        # Clean up
        db_session.delete(sess)
        db_session.commit()
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)


def test_chat_with_existing_session(client: TestClient, db_session):
    # Pre-create session
    sess = SessionModel(title="Existing Session")
    db_session.add(sess)
    db_session.commit()
    db_session.refresh(sess)

    mock_rag = AsyncMock()
    mock_rag.answer = AsyncMock(return_value={
        "content": "Follow-up response regarding growth loops.",
        "citations": [],
        "served_by": "ollama",
        "is_grounded": True,
    })

    app.dependency_overrides[get_rag_engine] = lambda: mock_rag
    try:
        response = client.post(
            "/api/chat",
            json={"session_id": str(sess.id), "message": "What about loops?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == str(sess.id)

        # Verify DB has 2 messages
        messages = db_session.query(MessageModel).filter(MessageModel.session_id == sess.id).all()
        assert len(messages) == 2

        # Clean up
        db_session.delete(sess)
        db_session.commit()
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)


def test_chat_nonexistent_session_returns_404(client: TestClient):
    fake_id = str(uuid.uuid4())
    response = client.post(
        "/api/chat",
        json={"session_id": fake_id, "message": "Hello?"},
    )
    assert response.status_code == 404
    assert f"Session '{fake_id}' not found" in response.json()["detail"]


def test_chat_strict_refusal_persistence(client: TestClient, db_session):
    mock_rag = AsyncMock()
    mock_rag.answer = AsyncMock(return_value={
        "content": "I couldn't find any discussion on neurosurgery in Lenny's Podcast transcripts.",
        "citations": [],
        "served_by": "system-groundedness",
        "is_grounded": False,
    })

    app.dependency_overrides[get_rag_engine] = lambda: mock_rag
    try:
        response = client.post(
            "/api/chat",
            json={"message": "How to perform brain surgery?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_grounded"] is False
        assert data["served_by"] == "system-groundedness"
        assert len(data["citations"]) == 0
        assert "neurosurgery" in data["content"]

        # Clean up session
        sess = db_session.query(SessionModel).filter(SessionModel.id == data["session_id"]).first()
        if sess:
            db_session.delete(sess)
            db_session.commit()
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)
