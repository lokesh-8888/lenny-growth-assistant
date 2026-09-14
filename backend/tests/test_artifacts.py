"""
Tests for multi-type artifact generation: Markdown briefs, HTML artifacts,
automated CSP injection, and sandboxed rendering safeguards.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import MessageModel, SessionModel, ArtifactModel
from app.schemas import StructureValidation
from app.skills.markdown_brief import MarkdownBriefSkill, get_markdown_skill
from app.skills.html_artifact import HtmlArtifactSkill, get_html_skill, ensure_csp_in_html, RESTRICTIVE_CSP_TAG


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


SAMPLE_MARKDOWN_BRIEF = """# Executive Brief: The Growth Engine Playbook

## Executive Summary
High-performing growth teams are fundamentally built on competency-based hiring rather than generalist titles. By structuring teams around 4 core pillars, companies achieve higher experimentation velocity and durable customer acquisition without inflating burn rates.

## Strategic Framework
* **Growth Execution**: Channel fluency, rapid experimentation velocity, and productizing learnings directly into the core user experience.
* **Customer Knowledge**: Quantitative data instrumentation, funnel analytics, and deep user psychology derived from qualitative interviews.
* **Growth Strategy**: Quantitative loop modeling, communication of growth loops, and capital allocation across channels.
* **Communication & Influence**: Cross-functional alignment, strategic roadmapping, and executive stakeholder management.

## Tactical Implementation Checklist
1. Conduct a comprehensive competency audit of existing growth team members.
2. Establish a unified metric instrumentation dashboard before launching any paid or viral growth loop experiments.
3. Implement weekly experiment debrief meetings to document learnings and translate them into product requirements.
4. Align quarterly OKRs with leading growth loop indicators rather than lagging revenue metrics.

## Key Metrics & KPIs
- Experiment throughput per engineer/PM (>3 experiments per week)
- Experiment win rate percentage (target 25% to 35%)
- Customer acquisition payback window (<12 months across all channels)

## Provenance Sources
- Adam Fishman, *How to build a high-performing growth team*, Lenny's Podcast
"""


SAMPLE_HTML_ARTIFACT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CAC Payback Simulator</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }
        .card { background: #1e293b; padding: 1.5rem; border-radius: 8px; max-width: 600px; margin: 0 auto; }
        .slider { width: 100%; margin: 1rem 0; }
        .metric { font-size: 2rem; color: #38bdf8; font-weight: bold; }
    </style>
</head>
<body>
    <div class="card">
        <h1>CAC Payback Period Simulator</h1>
        <p>Grounded in Lenny's Podcast operator benchmarks.</p>
        <label>Monthly ARPU ($): <span id="arpu-val">100</span></label>
        <input type="range" min="10" max="500" value="100" id="arpu" class="slider">
        <label>CAC ($): <span id="cac-val">600</span></label>
        <input type="range" min="50" max="2000" value="600" id="cac" class="slider">
        <div class="metric" id="payback">Payback: 6.0 Months</div>
    </div>
    <script>
        const arpu = document.getElementById('arpu');
        const cac = document.getElementById('cac');
        const payback = document.getElementById('payback');
        function update() {
            document.getElementById('arpu-val').textContent = arpu.value;
            document.getElementById('cac-val').textContent = cac.value;
            const months = (cac.value / arpu.value).toFixed(1);
            payback.textContent = 'Payback: ' + months + ' Months';
        }
        arpu.addEventListener('input', update);
        cac.addEventListener('input', update);
    </script>
</body>
</html>
"""


def test_markdown_skill_validation():
    skill = MarkdownBriefSkill()
    validation = skill.validate(SAMPLE_MARKDOWN_BRIEF)
    assert validation.is_valid is True
    assert validation.has_headings is True
    assert validation.has_bullets is True
    assert validation.has_bold is True
    assert validation.score >= 0.8
    assert len(validation.issues) == 0


def test_markdown_skill_validation_missing_elements():
    skill = MarkdownBriefSkill()
    validation = skill.validate("Short plain text without structure or headings.")
    assert validation.is_valid is False
    assert validation.has_headings is False
    assert validation.has_bullets is False
    assert len(validation.issues) > 0


def test_ensure_csp_in_html():
    # 1. HTML with <head> but no CSP -> Injected
    html_without_csp = "<html><head><title>Test</title></head><body><h1>Hi</h1></body></html>"
    secured = ensure_csp_in_html(html_without_csp)
    assert "Content-Security-Policy" in secured
    assert "default-src 'none'" in secured
    assert "style-src 'unsafe-inline'" in secured
    assert "script-src 'unsafe-inline'" in secured

    # 2. HTML already containing CSP -> Not duplicated
    assert secured.count("Content-Security-Policy") == 1
    secured_again = ensure_csp_in_html(secured)
    assert secured_again.count("Content-Security-Policy") == 1

    # 3. Bare HTML fragment without head or html tags -> Wrapped cleanly
    fragment = "<div class='calc'>Calculator</div>"
    wrapped = ensure_csp_in_html(fragment)
    assert "<!DOCTYPE html>" in wrapped
    assert "Content-Security-Policy" in wrapped
    assert "<div class='calc'>Calculator</div>" in wrapped


def test_html_skill_validation():
    skill = HtmlArtifactSkill()
    secured_html = ensure_csp_in_html(SAMPLE_HTML_ARTIFACT)
    validation = skill.validate(secured_html)
    assert validation.is_valid is True
    assert validation.has_hook is True
    assert validation.has_headings is True
    assert validation.has_bullets is True
    assert validation.has_bold is True
    assert validation.has_takeaway is True
    assert validation.score == 1.0


@pytest.mark.asyncio
async def test_markdown_skill_generate():
    mock_router = MagicMock()
    mock_router.complete = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = SAMPLE_MARKDOWN_BRIEF
    mock_response.served_by = "ollama"
    mock_router.complete.return_value = mock_response

    skill = MarkdownBriefSkill(router=mock_router)
    result = await skill.generate(
        context="Adam Fishman talks about growth teams.",
        topic="Executive Brief: The Growth Engine Playbook",
    )
    assert result["title"] == "Executive Brief: The Growth Engine Playbook"
    assert result["served_by"] == "ollama"
    assert result["validation"].is_valid is True


@pytest.mark.asyncio
async def test_html_skill_generate_enforces_csp():
    mock_router = MagicMock()
    mock_router.complete = AsyncMock()
    html_raw = "<html><head><title>Growth ROI Calculator</title><style>body{color:red;}</style></head><body><h1>Calc</h1></body></html>"
    mock_response = MagicMock()
    mock_response.content = html_raw
    mock_response.served_by = "ollama"
    mock_router.complete.return_value = mock_response

    skill = HtmlArtifactSkill(router=mock_router)
    result = await skill.generate(
        context="Elena Verna talks about product-led growth metrics.",
        topic="Growth ROI Calculator",
    )
    assert "Content-Security-Policy" in result["content"]
    assert "default-src 'none'" in result["content"]
    assert result["validation"].is_valid is True


def test_api_generate_markdown_artifact(client: TestClient, db_session: Session):
    session = SessionModel(title="Markdown Brief Test")
    db_session.add(session)
    db_session.commit()

    msg = MessageModel(
        session_id=session.id,
        role="assistant",
        content="Here is tactical growth insight.",
        citations=[{"guest": "Adam Fishman", "episode_title": "Growth Team", "source_url": "http://example.com"}],
    )
    db_session.add(msg)
    db_session.commit()

    mock_validation = StructureValidation(
        is_valid=True,
        word_count=450,
        target_word_count=750,
        has_hook=True,
        has_headings=True,
        has_bullets=True,
        has_bold=True,
        has_takeaway=True,
        score=1.0,
        issues=[],
    )

    mock_skill = MagicMock()
    mock_skill.generate = AsyncMock(
        return_value={
            "title": "Executive Brief: The Growth Engine Playbook",
            "content": SAMPLE_MARKDOWN_BRIEF,
            "word_count": 450,
            "validation": mock_validation,
            "citations": msg.citations,
            "served_by": "ollama",
        }
    )
    mock_skill.validate = MagicMock(return_value=mock_validation)

    app.dependency_overrides[get_markdown_skill] = lambda: mock_skill
    try:
        response = client.post(
            "/api/artifacts/generate",
            json={
                "session_id": str(session.id),
                "type": "markdown",
                "title": "Executive Brief: The Growth Engine Playbook",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "markdown"
        assert data["title"] == "Executive Brief: The Growth Engine Playbook"
        assert data["word_count"] == 450
        artifact_id = data["id"]

        get_resp = client.get(f"/api/artifacts/{artifact_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["id"] == artifact_id
        assert get_data["type"] == "markdown"
    finally:
        app.dependency_overrides.pop(get_markdown_skill, None)


def test_api_generate_html_artifact_enforces_csp(client: TestClient, db_session: Session):
    session = SessionModel(title="HTML Artifact Test")
    db_session.add(session)
    db_session.commit()

    msg = MessageModel(
        session_id=session.id,
        role="assistant",
        content="Here are growth calculation formulas.",
        citations=[{"guest": "Elena Verna", "episode_title": "B2B Growth", "source_url": "http://example.com"}],
    )
    db_session.add(msg)
    db_session.commit()

    mock_validation = StructureValidation(
        is_valid=True,
        word_count=350,
        target_word_count=350,
        has_hook=True,
        has_headings=True,
        has_bullets=True,
        has_bold=True,
        has_takeaway=True,
        score=1.0,
        issues=[],
    )

    mock_skill = MagicMock()
    mock_skill.generate = AsyncMock(
        return_value={
            "title": "CAC Payback Simulator",
            "content": SAMPLE_HTML_ARTIFACT,
            "word_count": 350,
            "validation": mock_validation,
            "citations": msg.citations,
            "served_by": "ollama",
        }
    )
    mock_skill.validate = MagicMock(return_value=mock_validation)

    app.dependency_overrides[get_html_skill] = lambda: mock_skill
    try:
        response = client.post(
            "/api/artifacts/generate",
            json={
                "session_id": str(session.id),
                "type": "html",
                "title": "CAC Payback Simulator",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "html"
        assert "Content-Security-Policy" in data["content"]
        assert "default-src 'none'" in data["content"]
        artifact_id = data["id"]

        db_artifact = db_session.query(ArtifactModel).filter(ArtifactModel.id == artifact_id).first()
        assert db_artifact is not None
        assert "Content-Security-Policy" in db_artifact.content
    finally:
        app.dependency_overrides.pop(get_html_skill, None)
