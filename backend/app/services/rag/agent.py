"""
RAGAgent orchestrator coordinating retrieval, grounded generation, citation extraction, and latency tracking.
"""

import time
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import MessageModel
from app.services.llm.router import LLMRouter, get_llm_router
from app.services.rag.prompts import (
    NOT_COVERED_MESSAGE,
    build_rag_messages,
    build_strict_refusal_response,
)
from app.services.rag.retriever import Retriever
from app.services.rag.types import Citation, RetrievedChunk


class RAGAgent:
    """
    Agent orchestrator: history assembly -> retrieval -> generation -> citation extraction.
    """

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        llm_router: Optional[LLMRouter] = None,
    ):
        self.retriever = retriever or Retriever()
        self.router = llm_router or get_llm_router()

    async def answer(
        self,
        query: str,
        db: Session,
        conversation_history: Optional[List[MessageModel]] = None,
        temperature: float = 0.7,
    ) -> Dict:
        """
        Executes grounded retrieval and generation.
        Returns a dictionary with content, citations, served_by, latency_ms, and is_grounded.
        """
        start_time = time.perf_counter()

        # 1. Retrieve relevant transcript chunks
        chunks = await self.retriever.retrieve(query=query, db=db)

        # 2. Strict refusal if no relevant excerpts pass the similarity threshold
        if not chunks:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "content": build_strict_refusal_response(query),
                "citations": [],
                "served_by": "system-groundedness",
                "latency_ms": elapsed_ms,
                "is_grounded": False,
            }

        # 3. Assemble messages with conversational history and formatted excerpts
        messages = build_rag_messages(
            user_query=query,
            chunks=chunks,
            conversation_history=conversation_history,
        )

        # 4. Generate response via LLMRouter
        llm_resp = await self.router.complete(
            messages=messages,
            temperature=temperature,
        )
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 5. Determine if generation was an honest refusal
        refusal_indicators = [
            "not covered in lenny's podcast",
            "could not find coverage",
            "not covered in the transcripts",
            "not covered in the excerpts",
            "transcripts do not cover",
        ]
        is_refusal = any(ind in llm_resp.content.lower() for ind in refusal_indicators)

        if is_refusal:
            return {
                "content": llm_resp.content,
                "citations": [],
                "served_by": llm_resp.served_by,
                "latency_ms": elapsed_ms,
                "is_grounded": False,
            }

        # 6. Extract deduplicated citations from the chunks used
        seen_titles = set()
        citations: List[Citation] = []
        for c in chunks:
            if c.episode_title not in seen_titles:
                seen_titles.add(c.episode_title)
                citations.append(
                    Citation(
                        episode_title=c.episode_title,
                        guest=c.guest,
                        source_url=c.source_url,
                    )
                )

        return {
            "content": llm_resp.content,
            "citations": citations,
            "served_by": llm_resp.served_by,
            "latency_ms": elapsed_ms,
            "is_grounded": True,
        }


# Alias for backward compatibility
RAGEngine = RAGAgent

_agent_instance: Optional[RAGAgent] = None


def get_rag_agent() -> RAGAgent:
    """Singleton accessor for RAGAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RAGAgent()
    return _agent_instance


get_rag_engine = get_rag_agent
