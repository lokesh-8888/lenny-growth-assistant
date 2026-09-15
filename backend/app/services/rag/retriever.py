"""
PostgreSQL pgvector cosine similarity retriever with hybrid keyword boosting.
"""

import re
from typing import List, Optional, Set
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.services.rag.embedder import QueryEmbedder
from app.services.rag.types import RetrievedChunk

STOPWORDS: Set[str] = {
    "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "would", "should", "could", "ought",
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at",
    "by", "for", "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then", "once", "here", "there",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "tell", "talk", "podcast", "lenny", "episode", "advice", "interview", "think",
}


def extract_keywords(query: str) -> List[str]:
    """Extracts non-stopword alphanumeric keywords from a query string."""
    words = re.findall(r"\b[A-Za-z0-9_-]+\b", query.lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


class Retriever:
    """
    Retrieves relevant transcript chunks using pgvector cosine distance
    with hybrid keyword boosting on episode and guest metadata.
    """

    def __init__(
        self,
        embedder: Optional[QueryEmbedder] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ):
        self.embedder = embedder or QueryEmbedder()
        self.top_k = top_k or settings.effective_top_k
        self.similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else settings.effective_similarity_threshold
        )

    async def retrieve(
        self,
        query: str,
        db: Session,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        Generates query embedding and executes cosine similarity search in PostgreSQL.
        """
        k = top_k or self.top_k
        min_sim = threshold if threshold is not None else self.similarity_threshold

        # 1. Embed user query
        query_vector = await self.embedder.embed_query(query)
        vector_str = f"[{','.join(f'{v:.6f}' for v in query_vector)}]"

        # 2. Fetch top 2*k nearest candidates via pgvector cosine distance (<=>)
        candidate_limit = max(k * 2, 10)
        sql = text(
            """
            SELECT 
                id,
                content,
                episode_title,
                guest,
                source_url,
                content_hash,
                timestamp,
                speaker,
                (embedding <=> CAST(:query_vector AS vector)) AS distance,
                1 - (embedding <=> CAST(:query_vector AS vector)) AS similarity
            FROM chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_vector AS vector) ASC
            LIMIT :candidate_limit;
            """
        )

        rows = db.execute(
            sql,
            {"query_vector": vector_str, "candidate_limit": candidate_limit},
        ).fetchall()

        if not rows:
            return []

        # 3. Hybrid keyword scoring on metadata
        keywords = extract_keywords(query)
        candidates: List[RetrievedChunk] = []

        for row in rows:
            if len(row) >= 10:
                chunk_id, content, title, guest, url, chash, chunk_ts, chunk_spk, dist, base_sim = row[:10]
            else:
                chunk_id, content, title, guest, url, chash, dist, base_sim = row[:8]
                chunk_ts, chunk_spk = None, None
            sim = float(base_sim) if base_sim is not None else 0.0
            distance_val = float(dist) if dist is not None else (1.0 - sim)

            # Boost if guest or title matches query keywords
            boost = 0.0
            title_lower = (title or "").lower()
            guest_lower = (guest or "").lower()

            for kw in keywords:
                if kw in guest_lower:
                    boost += 0.05
                elif kw in title_lower:
                    boost += 0.03

            total_sim = min(1.0, sim + boost)

            if total_sim >= min_sim:
                candidates.append(
                    RetrievedChunk(
                        id=chunk_id,
                        content=content,
                        episode_title=title or "Lenny's Podcast",
                        guest=guest or "Unknown Guest",
                        timestamp=chunk_ts,
                        speaker=chunk_spk,
                        source_url=url or "https://www.lennyspodcast.com",
                        content_hash=chash,
                        similarity=round(total_sim, 4),
                        distance=round(distance_val, 4),
                    )
                )

        # 4. Sort by final similarity score descending and take top_k
        candidates.sort(key=lambda c: c.similarity, reverse=True)
        return candidates[:k]
