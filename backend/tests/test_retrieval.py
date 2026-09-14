"""
Tests for RAG retrieval and embedding: QueryEmbedder, Retriever, and pgvector ranking.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.orm import Session

from app.models import ChunkModel
from app.services.rag.embedder import QueryEmbedder
from app.services.rag.prompts import (
    GROUNDED_SYSTEM_PROMPT,
    build_rag_messages,
    build_strict_refusal_response,
    format_context_chunks,
)
from app.services.rag.retriever import Retriever, extract_keywords
from app.services.rag.types import RetrievedChunk


# ---------------------------------------------------------------------------
# Unit Tests: QueryEmbedder
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_embedder_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={"embedding": [0.05] * 768})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        embedder = QueryEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        embedding = await embedder.embed_query("marketplace liquidity")

        assert len(embedding) == 768
        assert embedding[0] == 0.05
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_embedder_failure():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Ollama connection error")
        embedder = QueryEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        with pytest.raises(Exception):
            await embedder.embed_query("marketplace liquidity")


# ---------------------------------------------------------------------------
# Unit Tests: Keyword Extraction & Prompt Formatting
# ---------------------------------------------------------------------------
def test_keyword_extraction():
    keywords = extract_keywords("What did Dan Hockenmaier say about marketplaces?")
    assert "dan" in keywords
    assert "hockenmaier" in keywords
    assert "marketplaces" in keywords
    assert "what" not in keywords
    assert "about" not in keywords


def test_format_context_chunks():
    chunks = [
        RetrievedChunk(
            id=1,
            content="Retention is the single most important growth metric.",
            episode_title="Retention Strategies",
            guest="Casey Winters",
            source_url="https://youtube.com/watch?v=casey",
            content_hash="hash123",
            similarity=0.82,
            distance=0.18,
        )
    ]
    formatted = format_context_chunks(chunks)
    assert "--- Excerpt 1" in formatted
    assert "Casey Winters" in formatted
    assert "Retention Strategies" in formatted
    assert "Retention is the single most important growth metric." in formatted


# ---------------------------------------------------------------------------
# Unit Tests: Retriever Ranking & Cosine Similarity
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retrieval_ranking_and_keyword_boost():
    # Mock embedder to return a fixed 768-dim vector
    mock_embedder = AsyncMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 768)

    retriever = Retriever(embedder=mock_embedder, top_k=3, similarity_threshold=0.40)

    # Mock DB execute returning 3 candidate rows: (id, content, title, guest, url, chash, dist, base_sim)
    mock_db = MagicMock(spec=Session)
    mock_rows = [
        (1, "Generic product tactics.", "Product Ops", "Generic Guest", "url1", "h1", 0.35, 0.65),
        (2, "Casey on retention loops.", "Retention 101", "Casey Winters", "url2", "h2", 0.30, 0.70),
        (3, "Far off topic excerpt.", "Random Ep", "Random Guest", "url3", "h3", 0.75, 0.25),
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_rows

    results = await retriever.retrieve(query="What does Casey Winters say about retention?", db=mock_db)

    # Row 3 (base_sim 0.25) should be filtered out because 0.25 < threshold 0.40
    assert len(results) == 2

    # Row 2 should be boosted by "casey" and "winters" in guest name (+0.05) and ranked first
    assert results[0].id == 2
    assert results[0].guest == "Casey Winters"
    assert results[0].similarity > 0.70
    assert results[0].content_hash == "h2"
    assert results[0].distance == 0.30

    # Row 1 should be ranked second
    assert results[1].id == 1
    assert results[1].similarity == 0.65


@pytest.mark.asyncio
async def test_anti_hallucination_empty_retrieval_below_threshold():
    mock_embedder = AsyncMock()
    mock_embedder.embed_query = AsyncMock(return_value=[0.1] * 768)

    retriever = Retriever(embedder=mock_embedder, top_k=3, similarity_threshold=0.60)

    # All rows have similarity below the threshold
    mock_db = MagicMock(spec=Session)
    mock_rows = [
        (1, "Completely unrelated content.", "Ep 1", "Guest 1", "url1", "h1", 0.70, 0.30),
        (2, "More unrelated content.", "Ep 2", "Guest 2", "url2", "h2", 0.80, 0.20),
    ]
    mock_db.execute.return_value.fetchall.return_value = mock_rows

    results = await retriever.retrieve(
        query="Quantum astrophysics propulsion in Rust", db=mock_db
    )

    # Insufficient context flagged by returning empty list
    assert len(results) == 0
