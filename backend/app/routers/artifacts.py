"""
Artifact generation and retrieval router for Ship 30 essays, Markdown briefs, and HTML artifacts.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ArtifactModel, MessageModel, SessionModel
from app.schemas import (
    ArtifactGenerateRequest,
    ArtifactListItem,
    ArtifactResponse,
    ErrorResponse,
    StructureValidation,
)
from app.skills.ship30 import Ship30Skill, get_ship30_skill
from app.skills.markdown_brief import MarkdownBriefSkill, get_markdown_skill
from app.skills.html_artifact import HtmlArtifactSkill, get_html_skill, ensure_csp_in_html

router = APIRouter(tags=["Artifacts"])


@router.post(
    "/api/artifacts/generate",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a structured artifact (Ship 30 essay, Markdown brief, or HTML) from session context",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid artifact type or missing context"},
        404: {"model": ErrorResponse, "description": "Session or source message not found"},
    },
)
async def generate_artifact(
    payload: ArtifactGenerateRequest,
    db: Session = Depends(get_db),
    ship30_skill: Ship30Skill = Depends(get_ship30_skill),
    markdown_skill: MarkdownBriefSkill = Depends(get_markdown_skill),
    html_skill: HtmlArtifactSkill = Depends(get_html_skill),
):
    # 1. Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{payload.session_id}' not found",
        )

    # 2. Assemble context from session messages
    citations: List[dict] = []
    context_parts: List[str] = []

    if payload.source_message_id:
        target_msg = (
            db.query(MessageModel)
            .filter(
                MessageModel.id == payload.source_message_id,
                MessageModel.session_id == session.id,
            )
            .first()
        )
        if not target_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source message '{payload.source_message_id}' not found in session",
            )
        context_parts.append(f"[{target_msg.role.upper()}]:\n{target_msg.content}")
        if target_msg.citations:
            citations.extend(target_msg.citations)
    else:
        # Collect recent turns
        messages = (
            db.query(MessageModel)
            .filter(MessageModel.session_id == session.id)
            .order_by(MessageModel.created_at.asc())
            .all()
        )
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot generate an artifact from an empty session. Please ask a growth question first.",
            )
        for msg in messages:
            context_parts.append(f"[{msg.role.upper()}]:\n{msg.content}")
            if msg.citations and isinstance(msg.citations, list):
                for c in msg.citations:
                    if c not in citations:
                        citations.append(c)

    context_str = "\n\n".join(context_parts)

    # 3. Route to requested skill
    artifact_type = payload.type.lower().strip()
    topic = payload.title or session.title

    if artifact_type == "ship30":
        result = await ship30_skill.generate(
            context=context_str,
            topic=topic,
            citations=citations,
            model=payload.model,
        )
    elif artifact_type == "markdown":
        result = await markdown_skill.generate(
            context=context_str,
            topic=topic,
            citations=citations,
            model=payload.model,
        )
    elif artifact_type == "html":
        result = await html_skill.generate(
            context=context_str,
            topic=topic,
            citations=citations,
            model=payload.model,
        )
        # Enforce CSP tag in HTML before persistence
        result["content"] = ensure_csp_in_html(result["content"])
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported artifact type: '{payload.type}'. Supported types: ['ship30', 'markdown', 'html']",
        )

    # 4. Persist artifact record into database
    artifact = ArtifactModel(
        session_id=session.id,
        type=artifact_type,
        title=result["title"],
        content=result["content"],
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return ArtifactResponse(
        id=artifact.id,
        session_id=artifact.session_id,
        type=artifact.type,
        title=artifact.title,
        content=artifact.content,
        word_count=result["word_count"],
        validation=result.get("validation"),
        citations=result.get("citations", []),
        served_by=result.get("served_by"),
        created_at=artifact.created_at,
    )



@router.get(
    "/api/sessions/{session_id}/artifacts",
    response_model=List[ArtifactListItem],
    status_code=status.HTTP_200_OK,
    summary="List all artifacts generated for a specific session",
    responses={404: {"model": ErrorResponse, "description": "Session not found"}},
)
def list_session_artifacts(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    artifacts = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.session_id == session.id)
        .order_by(ArtifactModel.created_at.desc())
        .all()
    )

    items = []
    for a in artifacts:
        words = len(a.content.split())
        items.append(
            ArtifactListItem(
                id=a.id,
                session_id=a.session_id,
                type=a.type,
                title=a.title,
                word_count=words,
                created_at=a.created_at,
            )
        )
    return items


@router.get(
    "/api/artifacts/{artifact_id}",
    response_model=ArtifactResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single artifact by its ID",
    responses={404: {"model": ErrorResponse, "description": "Artifact not found"}},
)
def get_artifact(
    artifact_id: UUID,
    db: Session = Depends(get_db),
    ship30_skill: Ship30Skill = Depends(get_ship30_skill),
    markdown_skill: MarkdownBriefSkill = Depends(get_markdown_skill),
    html_skill: HtmlArtifactSkill = Depends(get_html_skill),
):
    artifact = db.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )

    # Perform structural validation on retrieved content according to artifact type
    if artifact.type == "markdown":
        validation = markdown_skill.validate(artifact.content)
    elif artifact.type == "html":
        validation = html_skill.validate(artifact.content)
    else:
        validation = ship30_skill.validate(artifact.content)

    return ArtifactResponse(
        id=artifact.id,
        session_id=artifact.session_id,
        type=artifact.type,
        title=artifact.title,
        content=artifact.content,
        word_count=validation.word_count,
        validation=validation,
        citations=[],
        served_by="database",
        created_at=artifact.created_at,
    )
