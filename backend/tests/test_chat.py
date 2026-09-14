"""
Integration tests for POST /api/chat endpoint: persistence, citations, multi-turn follow-up, and anti-hallucination.
"""

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import MessageModel, SessionModel
from app.services.rag.agent import RAGAgent, get_rag_agent
from app.services.rag.engine import get_rag_engine
from app.services.rag.types import Citation, RetrievedChunk


def test_anti_hallucination_refusal(client: TestClient, db_session):
    """Anti-hallucination test: unmentioned topics trigger honest refusal without hallucinating."""
    mock_agent = AsyncMock()
    mock_agent.answer = AsyncMock(return_value={
        "content": "I couldn't find coverage of this topic in the available Lenny's Podcast transcripts.",
        "citations": [],
        "served_by": "system-groundedness",
        "latency_ms": 15.2,
        "is_grounded": False,
    })

    app.dependency_overrides[get_rag_engine] = lambda: mock_agent
    try:
        response = client.post(
            "/api/chat",
            json={"message": "Quantum astrophysics propulsion in Rust"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_grounded"] is False
        assert data["served_by"] == "system-groundedness"
        assert len(data["citations"]) == 0
        assert "couldn't find coverage of this topic" in data["content"]

        # Verify persisted in database
        sess = db_session.query(SessionModel).filter(SessionModel.id == data["session_id"]).first()
        assert sess is not None

        # Clean up
        db_session.delete(sess)
        db_session.commit()
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)


def test_message_persistence_and_citations(client: TestClient, db_session):
    """Message persistence test: verify user and assistant records are written to messages table."""
    mock_agent = AsyncMock()
    mock_agent.answer = AsyncMock(return_value={
        "content": "According to Shreyas Doshi, great product managers focus on leverage and high-impact problem spaces.",
        "citations": [
            Citation(
                episode_title="Good Product Manager, Great Product Manager",
                guest="Shreyas Doshi",
                source_url="https://www.lennyspodcast.com/shreyas-doshi",
            )
        ],
        "served_by": "ollama",
        "latency_ms": 842.1,
        "is_grounded": True,
    })

    app.dependency_overrides[get_rag_engine] = lambda: mock_agent
    try:
        response = client.post(
            "/api/chat",
            json={"message": "What did Shreyas Doshi say about great product managers?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_grounded"] is True
        assert data["served_by"] == "ollama"
        assert data["latency_ms"] == 842.1
        assert len(data["citations"]) == 1
        assert data["citations"][0]["guest"] == "Shreyas Doshi"
        assert data["citations"][0]["episode_title"] == "Good Product Manager, Great Product Manager"

        # Verify records in database
        sess = db_session.query(SessionModel).filter(SessionModel.id == data["session_id"]).first()
        assert sess is not None

        messages = (
            db_session.query(MessageModel)
            .filter(MessageModel.session_id == sess.id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        assert len(messages) == 2

        # Turn 1: user
        assert messages[0].role == "user"
        assert messages[0].content == "What did Shreyas Doshi say about great product managers?"

        # Turn 2: assistant
        assert messages[1].role == "assistant"
        assert "According to Shreyas Doshi" in messages[1].content
        assert messages[1].served_by == "ollama"
        assert len(messages[1].citations) == 1
        assert messages[1].citations[0]["guest"] == "Shreyas Doshi"

        # Clean up
        db_session.delete(sess)
        db_session.commit()
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)


def test_multi_turn_followup_preserves_context(client: TestClient, db_session):
    """Multi-turn follow-up test: question followed by follow-up retains context and persists turns."""
    mock_agent = AsyncMock()

    # Turn 1: Airbnb growth
    mock_agent.answer.side_effect = [
        {
            "content": "Airbnb grew early on by focusing on high-quality photography and unscalable tactics.",
            "citations": [
                Citation(
                    episode_title="The Inside Story of Airbnb's Growth",
                    guest="Brian Chesky",
                    source_url="https://www.lennyspodcast.com/airbnb",
                )
            ],
            "served_by": "ollama",
            "latency_ms": 750.0,
            "is_grounded": True,
        },
        # Turn 2: Follow-up on Brian Chesky's role
        {
            "content": "Brian Chesky personally visited hosts in New York to photograph apartments himself.",
            "citations": [
                Citation(
                    episode_title="The Inside Story of Airbnb's Growth",
                    guest="Brian Chesky",
                    source_url="https://www.lennyspodcast.com/airbnb",
                )
            ],
            "served_by": "ollama",
            "latency_ms": 680.0,
            "is_grounded": True,
        },
    ]

    app.dependency_overrides[get_rag_engine] = lambda: mock_agent
    try:
        # Turn 1
        r1 = client.post(
            "/api/chat",
            json={"message": "Tell me about Airbnb's early growth"},
        )
        assert r1.status_code == 200
        data1 = r1.json()
        session_id = data1["session_id"]

        # Turn 2 (Follow-up using the same session_id)
        r2 = client.post(
            "/api/chat",
            json={
                "session_id": session_id,
                "message": "What about Brian Chesky's role?",
            },
        )
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["session_id"] == session_id
        assert "photograph apartments himself" in data2["content"]

        # Verify all 4 messages in DB
        messages = (
            db_session.query(MessageModel)
            .filter(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        assert len(messages) == 4
        assert messages[0].content == "Tell me about Airbnb's early growth"
        assert messages[1].content.startswith("Airbnb grew early on")
        assert messages[2].content == "What about Brian Chesky's role?"
        assert "Brian Chesky personally visited" in messages[3].content

        # Clean up
        sess = db_session.query(SessionModel).filter(SessionModel.id == session_id).first()
        if sess:
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
