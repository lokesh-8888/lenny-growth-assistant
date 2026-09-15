"""
Dedicated specification tests for Phase 2:
- Strict Groundedness & Honest Refusal
- Rich Citations with Timestamps & Quotes
- Ship 30 for 30 Skill Writing Framework & Word Count Validation
- Secure Multi-Type Artifacts & Automated CSP Injection
"""

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import ArtifactModel, MessageModel, SessionModel
from app.services.rag.engine import RAGEngine, get_rag_engine
from app.services.rag.prompts import (
    NOT_COVERED_MESSAGE,
    build_strict_refusal_response,
    format_context_chunks,
)
from app.services.rag.types import Citation, RetrievedChunk
from app.skills.html_artifact import RESTRICTIVE_CSP_TAG, ensure_csp_in_html
from app.skills.ship30 import Ship30Skill


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Strict Groundedness & Honest Refusal
# ---------------------------------------------------------------------------
def test_strict_groundedness_refusal_text():
    """Verify non-negotiable refusal text matches required specification."""
    expected_prefix = "I couldn't find coverage of this topic in the available Lenny's Podcast transcripts"
    assert expected_prefix in NOT_COVERED_MESSAGE

    refusal_with_query = build_strict_refusal_response("quantum gravity warp drive")
    assert expected_prefix in refusal_with_query


@pytest.mark.asyncio
async def test_rag_engine_strict_refusal_when_no_chunks_found():
    """Verify RAG engine returns honest refusal when retriever returns 0 chunks."""
    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])

    mock_router = MagicMock()
    engine = RAGEngine(retriever=mock_retriever, llm_router=mock_router)

    result = await engine.answer(
        query="Explain string theory in quantum mechanics",
        db=MagicMock(),
    )

    assert result["is_grounded"] is False
    assert result["served_by"] == "system-groundedness"
    assert len(result["citations"]) == 0
    assert "I couldn't find coverage of this topic in the available Lenny's Podcast transcripts" in result["content"]


# ---------------------------------------------------------------------------
# 2. Rich Citations with Timestamps and Quotes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rich_citations_formatting_with_timestamps_and_quotes():
    """Verify citations contain episode_title, guest, timestamp, source_url, and quote_snippet."""
    mock_chunk = RetrievedChunk(
        id=105,
        content="We don't have traditional product managers. We combined inbound product management with outbound product marketing.",
        episode_title="Brian Chesky's new playbook",
        guest="Brian Chesky",
        timestamp="00:05:56",
        speaker="Brian Chesky",
        source_url="https://www.youtube.com/watch?v=4ef0juAMqoE",
        content_hash="test_hash_105",
        similarity=0.88,
    )

    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[mock_chunk])

    mock_llm_resp = MagicMock()
    mock_llm_resp.content = "At Airbnb, Brian Chesky eliminated traditional PM roles and created product marketers."
    mock_llm_resp.served_by = "ollama:llama3.2:3b"

    mock_router = AsyncMock()
    mock_router.complete = AsyncMock(return_value=mock_llm_resp)

    engine = RAGEngine(retriever=mock_retriever, llm_router=mock_router)
    result = await engine.answer(query="How does Airbnb organize product managers?", db=MagicMock())

    assert result["is_grounded"] is True
    assert len(result["citations"]) == 1

    citation = result["citations"][0]
    assert citation.episode_title == "Brian Chesky's new playbook"
    assert citation.guest == "Brian Chesky"
    assert citation.timestamp == "00:05:56"
    assert citation.speaker == "Brian Chesky"
    assert citation.source_url == "https://www.youtube.com/watch?v=4ef0juAMqoE"
    assert citation.quote is not None
    assert citation.quote_snippet is not None
    assert "traditional product managers" in citation.quote_snippet


def test_format_context_chunks_includes_timestamp_and_speaker():
    """Verify format_context_chunks exposes timestamp and speaker in headers."""
    chunks = [
        RetrievedChunk(
            id=1,
            content="Insight on retention loops.",
            episode_title="Retention Strategy",
            guest="Casey Winters",
            timestamp="14:25",
            speaker="Casey Winters",
            source_url="https://example.com",
            content_hash="h1",
            similarity=0.75,
        )
    ]
    formatted = format_context_chunks(chunks)
    assert 'Timestamp: [14:25]' in formatted
    assert 'Speaker: Casey Winters' in formatted
    assert 'Retention Strategy' in formatted


# ---------------------------------------------------------------------------
# 3. Ship 30 for 30 Skill Writing Framework & Word Count
# ---------------------------------------------------------------------------
def test_ship30_skill_validation():
    """Verify Ship 30 validation enforces hook, headers, bullets, bolding, and takeaway."""
    skill = Ship30Skill(target_word_count=200, tolerance=0.50)

    valid_essay = """# The Counter-Intuitive Truth About Product Velocity

Why do 80% of feature launches fail to move metrics? Because engineering teams optimize for shipping speed instead of learning loops.

## The Status Quo: Feature Factories

Most product orgs run on a roadmap treadmill. They commit to 12-month roadmaps, deliver features on schedule, and celebrate shipping rather than adoption.

## The Core Insight: Competency-Driven Pods

Top growth operators structure teams differently:
- **Instrumentation First**: Validate event telemetry before writing production UI.
- **Rapid Prototyping**: Test low-fidelity mockups with 5 customers in 48 hours.
- **Durable Guardrails**: Establish failure metrics before running experiments.

## The One Takeaway

**Velocity is meaningless without direction.** Measure customer habit formation, not tickets closed.
"""
    validation = skill.validate(valid_essay)
    assert validation.has_hook is True
    assert validation.has_headings is True
    assert validation.has_bullets is True
    assert validation.has_bold is True
    assert validation.has_takeaway is True
    assert validation.is_valid is True
    assert validation.score >= 0.8


# ---------------------------------------------------------------------------
# 4. Secure Multi-Type Artifacts & CSP Injection
# ---------------------------------------------------------------------------
def test_html_artifact_automatic_csp_injection():
    """Verify strict CSP meta tag is injected into HTML artifacts."""
    raw_html = """<!DOCTYPE html>
<html>
<head>
    <title>Growth Calculator</title>
    <style>body { background: #14171F; color: #fff; }</style>
</head>
<body>
    <h1>CAC Payback Calculator</h1>
</body>
</html>"""

    secured_html = ensure_csp_in_html(raw_html)
    assert RESTRICTIVE_CSP_TAG in secured_html
    assert "default-src 'none'" in secured_html
    assert "style-src 'unsafe-inline'" in secured_html
    assert "script-src 'unsafe-inline'" in secured_html


def test_html_artifact_skeleton_injection_when_head_missing():
    """Verify ensure_csp_in_html wraps bare snippets with a valid secured skeleton."""
    bare_snippet = "<div class='calculator'><h2>LTV Calculator</h2></div>"
    secured = ensure_csp_in_html(bare_snippet)

    assert "<!DOCTYPE html>" in secured
    assert RESTRICTIVE_CSP_TAG in secured
    assert bare_snippet in secured


# ---------------------------------------------------------------------------
# 5. Endpoints Integration: Chat & Artifact Generation
# ---------------------------------------------------------------------------
def test_chat_and_artifact_generation_flow(client: TestClient, db_session: Session):
    """Test full chat session flow and artifact creation."""
    # 1. Create a session
    sess_resp = client.post("/api/sessions", json={"title": "Phase 2 Test Session"})
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["id"]

    # 2. Mock RAG response
    mock_rag = AsyncMock()
    mock_rag.answer = AsyncMock(return_value={
        "content": "Brian Chesky emphasizes deep founder involvement in product details.",
        "citations": [
            Citation(
                episode_title="Brian Chesky's new playbook",
                guest="Brian Chesky",
                timestamp="00:05:56",
                speaker="Brian Chesky",
                source_url="https://www.youtube.com/watch?v=4ef0juAMqoE",
                quote="We don't have traditional product managers.",
                quote_snippet="We don't have traditional product managers.",
            )
        ],
        "served_by": "ollama:llama3.2:3b",
        "is_grounded": True,
    })

    app.dependency_overrides[get_rag_engine] = lambda: mock_rag

    try:
        # 3. Post chat message
        chat_resp = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": "What did Brian Chesky say about PMs?"},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert chat_data["served_by"] == "ollama:llama3.2:3b"
        assert len(chat_data["citations"]) == 1
        assert chat_data["citations"][0]["timestamp"] == "00:05:56"
        assert chat_data["citations"][0]["guest"] == "Brian Chesky"

        # 4. Generate an HTML artifact from this session
        art_resp = client.post(
            "/api/artifacts/generate",
            json={
                "session_id": session_id,
                "type": "html",
                "title": "Interactive PM Assessment",
            },
        )
        assert art_resp.status_code == 201
        art_data = art_resp.json()
        assert art_data["type"] == "html"
        assert RESTRICTIVE_CSP_TAG in art_data["content"]
        assert "default-src 'none'" in art_data["content"]

        # 5. Verify list session artifacts
        list_art_resp = client.get(f"/api/sessions/{session_id}/artifacts")
        assert list_art_resp.status_code == 200
        assert len(list_art_resp.json()) >= 1
    finally:
        app.dependency_overrides.pop(get_rag_engine, None)
        sess = db_session.query(SessionModel).filter(SessionModel.id == session_id).first()
        if sess:
            db_session.delete(sess)
            db_session.commit()
