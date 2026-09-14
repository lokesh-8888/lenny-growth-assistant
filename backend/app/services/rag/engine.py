"""
RAGEngine coordinating retrieval, grounded generation, citation compilation, and refusal paths.
"""

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


class RAGEngine:
    """
    Orchestrates grounded question answering over Lenny's Podcast transcripts.
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
        Returns a dictionary with content, citations, served_by, and is_grounded.
        """
        # 1. Retrieve relevant transcript chunks
        chunks = await self.retriever.retrieve(query=query, db=db)

        # 2. Strict refusal if no relevant excerpts pass the similarity threshold
        if not chunks:
            return {
                "content": build_strict_refusal_response(query),
                "citations": [],
                "served_by": "system-groundedness",
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
            "is_grounded": True,
        }


_engine_instance: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Singleton accessor for RAGEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RAGEngine()
    return _engine_instance
