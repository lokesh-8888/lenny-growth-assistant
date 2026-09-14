"""
Conversational RAG Chat router with session persistence and citation attribution.
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import MessageModel, SessionModel
from app.schemas import ErrorResponse
from app.services.rag.engine import RAGEngine, get_rag_engine
from app.services.rag.types import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message and receive a grounded answer with citations",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
async def chat_completion(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    rag_engine: RAGEngine = Depends(get_rag_engine),
):
    # 1. Resolve or create session
    if payload.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{payload.session_id}' not found",
            )
    else:
        title = payload.message[:50].strip()
        if len(payload.message) > 50:
            title += "..."
        session = SessionModel(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. Persist user question
    user_msg = MessageModel(
        session_id=session.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Retrieve recent conversational history for follow-ups
    history_records = (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session.id, MessageModel.id != user_msg.id)
        .order_by(MessageModel.created_at.desc())
        .limit(settings.rag_history_turns)
        .all()
    )
    history_records.reverse()

    # 4. Execute RAG pipeline
    rag_result = await rag_engine.answer(
        query=payload.message,
        db=db,
        conversation_history=history_records,
        temperature=payload.temperature or 0.7,
    )

    # 5. Persist assistant response with citations and provider info
    citations_data = [c.model_dump() for c in rag_result["citations"]]
    asst_msg = MessageModel(
        session_id=session.id,
        role="assistant",
        content=rag_result["content"],
        citations=citations_data,
        served_by=rag_result["served_by"],
    )
    session.updated_at = datetime.now(timezone.utc)

    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    return ChatResponse(
        session_id=session.id,
        message_id=asst_msg.id,
        role="assistant",
        content=asst_msg.content,
        citations=rag_result["citations"],
        served_by=asst_msg.served_by or "ollama",
        is_grounded=rag_result["is_grounded"],
    )
