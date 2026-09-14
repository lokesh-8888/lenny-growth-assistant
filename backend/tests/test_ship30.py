"""
Unit and integration tests for Ship 30 for 30 skill, structural validator, and artifact endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ArtifactModel, MessageModel, SessionModel
from app.schemas import StructureValidation
from app.skills.ship30 import Ship30Skill, get_ship30_skill


SAMPLE_SHIP30_ESSAY = """# How To Build A High-Velocity Growth Engine

Why do 90% of series B startups stall out on user acquisition? Because they hire growth specialists before discovering where their conversion leaks actually exist.

## The Status Quo: Throwing Money at Paid Channels

Most early-stage founders treat growth as a media-buying problem. They hire a Facebook or Google ads agency, burn $50,000 a month on customer acquisition cost (CAC), and watch their retention cohort charts drop like a stone after Day 7.

As **Adam Fishman** (former VP of Growth at Patreon and Lyft) points out in his interview on Lenny's Podcast, this is the quickest way to kill runway. A marketing channel cannot compensate for an unactivated user.

## The Core Insight: Competency-Driven Growth

High-performing growth operators don't look at single channels. They view growth through four distinct competency lenses:

- **Growth Execution**: Rapid-cadence experimentation and productizing learnings directly into software rather than disposable landing pages.
- **Customer Knowledge**: Combining quantitative instrumentation with qualitative customer psychology.
- **Growth Strategy**: Rigorous loop modeling rather than linear funnel thinking.
- **Communication and Influence**: Aligning cross-functional engineering, product, and marketing leaders around a shared north-star metric.

When you hire or cultivate people around these core competencies, growth ceases to be an isolated department and becomes the connective tissue of the entire company.

## The 3-Step Implementation Blueprint

1. **Audit Your Activation Threshold**: Identify the specific 'aha' moment where users become habitual. At Patreon, this meant getting creators their first pledge within 14 days.
2. **Form Dedicated Multi-Functional Pods**: Pair one dedicated engineer with one analyst and one product designer.
3. **Institutionalize Weekly Experiment Cadence**: Run at least three rigorous A/B hypotheses per week. Document every failure in an open knowledge repository so your organization never tests the same anti-pattern twice.

## The One Takeaway

**Never scale channel acquisition until your core activation loop demonstrates baseline retention.** Growth is an operational operating system, not a marketing campaign.

## Sources & References
- *How to build a high-performing growth team*, featuring **Adam Fishman** (Lenny's Podcast)
"""


# ---------------------------------------------------------------------------
# Unit Tests: Structure & Word Count Validator
# ---------------------------------------------------------------------------
def test_structure_validator_valid_essay():
    skill = Ship30Skill(target_word_count=340, tolerance=0.20)
    validation = skill.validate(SAMPLE_SHIP30_ESSAY)

    assert validation.has_headings is True
    assert validation.has_bullets is True
    assert validation.has_bold is True
    assert validation.has_takeaway is True
    assert validation.has_hook is True
    assert validation.word_count > 100
    assert validation.score >= 0.8
    assert validation.is_valid is True


def test_structure_validator_missing_elements():
    skill = Ship30Skill(target_word_count=1250, tolerance=0.20)
    plain_text = "Just some plain text without any markdown or formatting whatsoever."
    validation = skill.validate(plain_text)

    assert validation.is_valid is False
    assert validation.has_headings is False
    assert validation.has_bullets is False
    assert validation.has_bold is False
    assert validation.has_takeaway is False
    assert any("headings" in issue.lower() for issue in validation.issues)
    assert any("takeaway" in issue.lower() for issue in validation.issues)
    assert validation.score < 0.5


def test_validator_word_count_boundaries():
    skill = Ship30Skill(target_word_count=1000, tolerance=0.20)
    # 1000 words target with 0.20 tolerance -> min: 800, max: 1200

    short_essay = "## Heading\n\n- **Item**: " + "word " * 600 + "\n\n## The One Takeaway\nFinal point."
    val_short = skill.validate(short_essay)
    assert any("below minimum target" in issue.lower() for issue in val_short.issues)

    long_essay = "## Heading\n\n- **Item**: " + "word " * 1300 + "\n\n## The One Takeaway\nFinal point."
    val_long = skill.validate(long_essay)
    assert any("exceeds maximum target" in issue.lower() for issue in val_long.issues)


# ---------------------------------------------------------------------------
# Unit Tests: Skill Generation & Grounding
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ship30_skill_generation():
    mock_llm = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.content = SAMPLE_SHIP30_ESSAY
    mock_resp.served_by = "ollama"
    mock_llm.complete = AsyncMock(return_value=mock_resp)

    skill = Ship30Skill(llm_router=mock_llm, target_word_count=200, tolerance=0.50)
    result = await skill.generate(
        context="Adam Fishman discussed growth competencies at Patreon and Lyft.",
        topic="Building Growth Teams",
        citations=[{"episode_title": "Growth Teams", "guest": "Adam Fishman"}],
        auto_refine=False,
    )

    assert "Adam Fishman" in result["content"]
    assert result["title"] == "How To Build A High-Velocity Growth Engine"
    assert result["served_by"] == "ollama"
    assert result["validation"].has_takeaway is True
    assert result["validation"].has_headings is True
    mock_llm.complete.assert_called_once()


# ---------------------------------------------------------------------------
# Integration Tests: Artifact API Endpoints
# ---------------------------------------------------------------------------
def test_generate_artifact_endpoint(client: TestClient, db_session):
    # 1. Setup session and conversation turns
    session = SessionModel(title="Growth Strategy Session")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    user_msg = MessageModel(
        session_id=session.id,
        role="user",
        content="How do you build a growth engine according to Adam Fishman?",
    )
    asst_msg = MessageModel(
        session_id=session.id,
        role="assistant",
        content="Adam Fishman says you need four core competencies: execution, customer knowledge, strategy, and communication.",
        citations=[
            {
                "episode_title": "How to build a high-performing growth team",
                "guest": "Adam Fishman",
                "source_url": "https://lennyspodcast.com/transcript",
            }
        ],
        served_by="ollama",
    )
    db_session.add_all([user_msg, asst_msg])
    db_session.commit()

    # 2. Mock Ship30Skill
    mock_skill = AsyncMock(spec=Ship30Skill)
    mock_validation = StructureValidation(
        is_valid=True,
        word_count=345,
        target_word_count=1250,
        has_hook=True,
        has_headings=True,
        has_bullets=True,
        has_bold=True,
        has_takeaway=True,
        score=1.0,
        issues=[],
    )

    mock_skill.validate.return_value = mock_validation
    mock_skill.generate = AsyncMock(return_value={
        "title": "How To Build A High-Velocity Growth Engine",
        "content": SAMPLE_SHIP30_ESSAY,
        "word_count": 345,
        "validation": mock_validation,
        "citations": asst_msg.citations,
        "served_by": "ollama",
    })

    app.dependency_overrides[get_ship30_skill] = lambda: mock_skill
    try:
        response = client.post(
            "/api/artifacts/generate",
            json={
                "session_id": str(session.id),
                "type": "ship30",
                "title": "Custom Growth Essay",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == str(session.id)
        assert data["type"] == "ship30"
        assert data["title"] == "How To Build A High-Velocity Growth Engine"
        assert "Adam Fishman" in data["content"]
        assert len(data["citations"]) == 1
        assert data["citations"][0]["guest"] == "Adam Fishman"

        artifact_id = data["id"]

        # 3. Verify single artifact retrieval
        get_resp = client.get(f"/api/artifacts/{artifact_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == artifact_id
        assert get_data["title"] == "How To Build A High-Velocity Growth Engine"

        # 4. Verify session artifacts list
        list_resp = client.get(f"/api/sessions/{session.id}/artifacts")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert len(list_data) == 1
        assert list_data[0]["id"] == artifact_id

        # Clean up
        db_session.delete(session)
        db_session.commit()
    finally:
        app.dependency_overrides.pop(get_ship30_skill, None)


def test_generate_artifact_empty_session_returns_400(client: TestClient, db_session):
    session = SessionModel(title="Empty Session")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    response = client.post(
        "/api/artifacts/generate",
        json={"session_id": str(session.id), "type": "ship30"},
    )
    assert response.status_code == 400
    assert "Cannot generate an artifact from an empty session" in response.json()["detail"]

    db_session.delete(session)
    db_session.commit()


def test_generate_artifact_unsupported_type_returns_400(client: TestClient, db_session):
    session = SessionModel(title="Session with Turns")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    msg = MessageModel(session_id=session.id, role="user", content="Hello!")
    db_session.add(msg)
    db_session.commit()

    response = client.post(
        "/api/artifacts/generate",
        json={"session_id": str(session.id), "type": "unsupported_format"},
    )
    assert response.status_code == 400
    assert "Unsupported artifact type" in response.json()["detail"]

    db_session.delete(session)
    db_session.commit()
