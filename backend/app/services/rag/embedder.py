"""
Embedding client for generating query vectors via Ollama nomic-embed-text.
"""

from typing import List, Optional
import httpx

from app.config import settings


class QueryEmbedder:
    """Generates dense vector embeddings for search queries."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.embedding_model
        self.timeout = timeout

    async def embed_query(self, query: str) -> List[float]:
        """Generates 768-dimensional embedding for a query string."""
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if not embedding or not isinstance(embedding, list):
                raise ValueError(f"Invalid embedding received from Ollama: {data}")
            return embedding
