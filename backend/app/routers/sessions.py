"""
Router for Chat Sessions and Messages persistence.
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MessageModel, SessionModel
from app.schemas import (
    ErrorResponse,
    MessageCreate,
    MessageResponse,
    SessionCreate,
    SessionResponse,
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
def create_session(payload: SessionCreate = SessionCreate(), db: Session = Depends(get_db)):
    session = SessionModel(
        title=payload.title,
        metadata_=payload.metadata or {},
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get(
    "",
    response_model=List[SessionResponse],
    summary="List all chat sessions ordered by updated_at descending",
)
def list_sessions(db: Session = Depends(get_db)):
    return (
        db.query(SessionModel)
        .order_by(SessionModel.updated_at.desc())
        .all()
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get single session metadata",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return session


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session and cascade delete its messages",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
def delete_session(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    db.delete(session)
    db.commit()
    return None


@router.get(
    "/{session_id}/messages",
    response_model=List[MessageResponse],
    summary="Fetch all messages for a session in chronological order",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
def get_session_messages(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
        .all()
    )


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append a new message to a session",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
def create_message(
    session_id: UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    message = MessageModel(
        session_id=session_id,
        role=payload.role,
        content=payload.content,
        citations=payload.citations or [],
        served_by=payload.served_by,
    )
    # Touch session updated_at
    session.updated_at = datetime.now(timezone.utc)

    db.add(message)
    db.commit()
    db.refresh(message)
    return message
