# The Lenny Growth Assistant

A local-first, zero-cost AI Growth and Product Assistant grounded in 260+ episodes of **Lenny's Podcast**. Ask tactical questions and receive answers cited directly from experienced operators, or generate structured growth frameworks and Ship 30/30 essays.

---

## Zero-Cost Stack

- **Storage**: PostgreSQL 16 with `pgvector` running locally via Docker Compose.
- **Embeddings**: Local Ollama running `nomic-embed-text` (768-dimensional embeddings, 100% free, no API key).
- **LLM**: Local Ollama (`llama3.2:3b` or `qwen2.5:7b-instruct`) with optional free cloud fallback (Groq / Gemini free tiers).
- **Knowledge Base**: Curated transcripts from [`ChatPRD/lennys-podcast-transcripts`](https://github.com/ChatPRD/lennys-podcast-transcripts) (269 Markdown transcripts with YAML frontmatter).
- **Backend / Orchestration**: FastAPI (Python 3.11+) asynchronous API with SQLAlchemy persistence.

---

## Prerequisites

1. **Docker Desktop** installed and running.
2. **Ollama** installed and running on `http://localhost:11434`.
3. Pull the embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```
4. **Python 3.11+** installed locally.

---

## Quickstart

### 1. Configure Environment
Copy the example environment file:
```bash
cp .env.example .env
```
All defaults are configured for seamless local operation out of the box.

### 2. Start Services via Docker Compose
Start PostgreSQL (with `pgvector`) and the FastAPI backend:
```bash
docker compose up -d
```
- PostgreSQL is available at `localhost:5432`.
- FastAPI Backend is available at `http://localhost:8000` (interactive Swagger docs at `http://localhost:8000/docs`).

To run only the database service in Docker:
```bash
docker compose up -d postgres
```

### 3. Local Backend Development (Standalone)
If running the backend outside Docker for local iteration:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Start FastAPI server:
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 4. Run Data Ingestion

Execute the ingestion pipeline:
```bash
python scripts/ingest.py
```

#### CLI Options & Flags:
- `python scripts/ingest.py` — Clones/verifies the transcript archive in `data/raw/` and ingests new or changed files into the database.
- `python scripts/ingest.py --refresh` — Specifically checks all files and only processes transcripts whose file hashes have changed or are not yet present in the database.
- `python scripts/ingest.py --limit 5` — Ingests only the first N files (ideal for rapid smoke testing and evaluation).
- `python scripts/ingest.py --force` — Forces re-processing and re-embedding of all files regardless of stored hashes.

#### Knowledge Base Source
The transcripts are sourced from [`ChatPRD/lennys-podcast-transcripts`](https://github.com/ChatPRD/lennys-podcast-transcripts). This repository provides 269 complete episodes in structured Markdown with YAML frontmatter (episode title, guest name, source URL, date), making it the highest quality open archive available. If you already have a local copy, set `RAW_DATA_PATH=/path/to/transcripts` in your `.env` file to skip downloading.

---

## API Endpoints (Phase 2)

### Health Check
- `GET /health`: Multi-component granular health status reporting:
  - **PostgreSQL**: connection status and query latency in milliseconds (`latency_ms`).
  - **Ollama**: reachability status and array of locally installed models (`models_available`).
  - **Cloud LLM**: provider configuration status (`configured: true/false`, non-paid check).
  - Overall status: `healthy` (200 OK), `degraded` (200 OK, e.g. Ollama unreachable), or `unhealthy` (503 Service Unavailable, DB disconnected).

### Sessions & Persistence
- `POST /api/sessions`: Create a new session with optional `title` and `metadata`.
- `GET /api/sessions`: List all sessions ordered by `updated_at` descending.
- `GET /api/sessions/{session_id}`: Retrieve single session metadata.
- `DELETE /api/sessions/{session_id}`: Delete a session and cascade delete its messages and artifacts.
- `GET /api/sessions/{session_id}/messages`: Fetch all messages for a session in chronological order (`created_at ASC`).
- `POST /api/sessions/{session_id}/messages`: Append a message (`role`, `content`, optional `citations`, optional `served_by`).

### Configuration & LLM Routing (Phase 3)
- `GET /api/config`: Introspect active LLM router status and available models:
  ```json
  {
    "current_provider": "ollama",
    "current_model": "llama3.1:8b",
    "fallback_provider": "ollama",
    "fallback_model": "llama3.1:8b",
    "available_providers": ["ollama", "groq", "gemini"],
    "cloud_configured": false
  }
  ```

### Grounded RAG Chat (Phase 4)
- `POST /api/chat`: Send a question and receive a strictly grounded answer with structured citations:
  ```json
  // Request
  {
    "session_id": "56077338-9877-4f93-a57e-a942b7f7baf3", // optional
    "message": "What does Adam Fishman say about building a growth team?",
    "temperature": 0.7
  }
  ```
  ```json
  // Response
  {
    "session_id": "56077338-9877-4f93-a57e-a942b7f7baf3",
    "message_id": "0a930f68-3f23-4ea2-b5f0-b0ceb59f55ba",
    "role": "assistant",
    "content": "Based on the transcript excerpts, here are the key points Adam Fishman makes...",
    "citations": [
      {
        "episode_title": "How to build a high-performing growth team | Adam Fishman (Patreon, Lyft, Imperfect Foods)",
        "guest": "Adam Fishman",
        "source_url": "https://www.lennyspodcast.com/transcript"
      }
    ],
    "served_by": "ollama",
    "is_grounded": true
  }
  ```
  - **Strict Groundedness Guardrail**: If retrieved transcript similarity falls below threshold or the topic is not covered in Lenny's Podcast archives, the engine guarantees an honest refusal (`"is_grounded": false`, empty citations) rather than hallucinating.
  - **Multi-turn Context**: Automatically includes recent session messages (up to `RAG_HISTORY_TURNS=6`) so contextual follow-ups ("Can you summarize his 4 points into a list?") work seamlessly.
  - **Auto-Persistence**: Sessions and both user and assistant messages with citations and provider tracking are automatically persisted to PostgreSQL.

### Ship 30 for 30 Essay Generation (Phase 5)

Generates viral, highly actionable, long-form growth essays adhering strictly to the **Ship 30 for 30** editorial framework, fully grounded in podcast transcript context and saved to the `artifacts` table.

#### The 5 Editorial Pillars
1. **Strong Opening Hook**: A compelling question, bold counter-intuitive claim, or vivid operator scenario.
2. **Clear Narrative Arc**: Setup (the status quo / problem) $\rightarrow$ Tension / Core Insight (what high-growth leaders do differently) $\rightarrow$ Resolution (tactical implementation).
3. **Skimmable Formatting**: Clean Markdown headings (`##`, `###`), structured bullet points / numbered steps, and selective **bolding** for rapid skimming.
4. **One Central Restated Takeaway**: A dedicated concluding section summarizing the single most actionable rule of thumb.
5. **Source Provenance**: Footnotes or inline attributions citing the specific guest name and podcast episode for every key insight.

#### Endpoints
- `POST /api/artifacts/generate`: Generate a structured artifact from conversation context.
  - Supported `type` options:
    - `"ship30"`: Long-form growth essay (~1,250 words) adhering to the 5 Ship 30 pillars.
    - `"markdown"`: Executive brief, teardown summary, or tactical implementation checklist.
    - `"html"`: Complete standalone HTML document with embedded CSS and interactive JS widgets.
  ```json
  // Request
  {
    "session_id": "56077338-9877-4f93-a57e-a942b7f7baf3",
    "type": "html",
    "title": "Interactive CAC Payback Simulator",
    "source_message_id": null
  }
  ```
  ```json
  // Response
  {
    "id": "c6ca89cc-939c-42fa-83d8-342ecb14fbe9",
    "session_id": "56077338-9877-4f93-a57e-a942b7f7baf3",
    "type": "html",
    "title": "Interactive CAC Payback Simulator",
    "content": "<!DOCTYPE html><html><head><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';\">...</head><body>...</body></html>",
    "word_count": 350,
    "validation": {
      "is_valid": true,
      "word_count": 350,
      "target_word_count": 350,
      "has_hook": true,
      "has_headings": true,
      "has_bullets": true,
      "has_bold": true,
      "has_takeaway": true,
      "score": 1.0,
      "issues": []
    },
    "citations": [
      {
        "guest": "Elena Verna",
        "episode_title": "B2B Growth & Payback Period Benchmarks",
        "source_url": "https://www.lennyspodcast.com/transcript"
      }
    ],
    "created_at": "2026-09-15T01:50:00.000000Z"
  }
  ```
- `GET /api/sessions/{session_id}/artifacts`: List all generated artifacts for a session.
- `GET /api/artifacts/{artifact_id}`: Fetch single artifact by ID with on-the-fly validation metrics.

#### Sandboxed Artifact Viewer & Dual-Pane UI (Phase 6 & 7)

The React frontend includes a responsive dual-pane workspace with seamless end-to-end user workflows:
1. **Interactive Chat Stream**:
   - Empty state hero with 4 curated operator starter queries (Adam Fishman competencies, Elena Verna loops, Cold start tactics, CAC payback benchmarks).
   - Auto-resizing input box with Enter-to-send and Shift+Enter for multiline questions.
   - Markdown rendering for assistant answers (lists, headings, bold callouts, blockquotes).
   - **Collapsible Citations Section**: Displays grounded transcript sources, speaker names, episode titles, and links to transcripts.
   - **Quick Action Toolbar**: One-click generation of Ship 30 Essays, Executive Briefs, or standalone HTML widgets directly below assistant answers.
2. **Dual-Pane Sandboxed Artifact Viewer**:
   - Mounts smoothly in the right pane alongside the conversation stream with **zero full-page reload**.
   - **Rendered View**:
     - Renders interactive HTML in a strictly isolated `<iframe sandbox="allow-scripts">` with **no `allow-same-origin`**.
     - Pre-sanitizes HTML via `DOMPurify` to eliminate remote script sources (`<script src="...">`).
     - Injects mandatory restrictive Content Security Policy: `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';">`.
     - Renders Markdown and Ship 30 essays in styled typographic layouts with callouts and bold highlights.
   - **Raw Source View**:
     - Preformatted monospaced code view with one-click **Copy Source** and **Download (.html / .md)** buttons.
   - Expandable fullscreen mode or collapsible single-pane mode.
3. **Telemetry & Resilience Transparency**:
   - Header badge actively displays serving LLM (`Ollama: llama3.1:8b`).
   - Dynamic health dot (`Healthy`, `Degraded`, `Offline`) polling `/health`.
   - Real-time fallback warning banner when cloud rate limits trigger automatic routing to local Ollama.

---

## Running Automated Tests

### Backend Test Suite (pytest)
Run pytest across the entire backend test suite (ingestion, retrieval, health, sessions, RAG chat, Ship 30, and multi-type artifacts):
```bash
# In project root:
pytest -v
# Or using the local virtualenv:
.venv\Scripts\pytest -v
```
All 65 backend tests pass across ingestion, retrieval, health, chat, and artifact generation.

### Frontend Test Suite (Vitest)
Run Vitest unit, security, and component tests:
```bash
cd frontend
npm test
```
All 23 frontend unit, integration, and security verification tests pass:
- `sanitize.test.ts`: DOMPurify sanitization & script strip verification.
- `SandboxedIframe.test.tsx`: Sandboxed iframe attributes (`allow-scripts` without `allow-same-origin`).
- `security.test.tsx`: XSS prevention and CSP meta tag enforcement.
- `SessionList.test.tsx`: Sessions list rendering, search filtering, "+ New Chat", and session deletion.
- `ChatFlow.test.tsx`: Starter queries, chat message dispatch, citation cards, and fallback badges.
- `ArtifactViewer.test.tsx`: Dual-view tabs (Rendered vs. Raw Source), copy to clipboard, and Markdown rendering.
- `ArtifactAction.test.tsx`: Quick action buttons, artifact generation, and sandboxed viewer mount with zero page reload.

---

## Running the Frontend Locally (Phase 7)

1. Start the backend on `http://localhost:8000`:
   ```bash
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
2. In a separate terminal, start the Vite development server:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:5173` in your browser. All API requests (`/api/*`, `/health`) are automatically proxied to the backend.

---

## Project Structure

```
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── config.py         # Pydantic settings (inc. RAG & SHIP30 params)
│   │   ├── database.py       # SQLAlchemy engine & session factory
│   │   ├── models.py         # SQLAlchemy ORM models (sessions, messages, chunks, artifacts)
│   │   ├── schemas.py        # Pydantic schemas (sessions, messages, rag, artifacts)
│   │   ├── routers/
│   │   │   ├── health.py     # Multi-component /health endpoint
│   │   │   ├── sessions.py   # Sessions & messages REST endpoints
│   │   │   ├── chat.py       # Grounded RAG chat endpoint
│   │   │   ├── config.py     # LLM router introspection endpoint
│   │   │   └── artifacts.py  # Artifact generation & retrieval endpoints
│   │   ├── services/
│   │   │   ├── llm/          # LLM router, Ollama, and cloud providers
│   │   │   └── rag/          # Grounded retrieval, prompt builder, citations
│   │   ├── skills/
│   │   │   ├── __init__.py   # Skills module exports
│   │   │   ├── base.py       # BaseSkill abstract interface
│   │   │   └── ship30.py     # Ship 30 for 30 skill generator & validator
│   │   └── main.py           # FastAPI entrypoint, CORS, exception handlers
│   ├── db/
│   │   ├── init.sql          # Postgres extension initialization
│   │   └── schema.sql        # Tables: chunks, sessions, messages, artifacts
│   ├── tests/
│   │   ├── conftest.py       # Test fixtures and database setup
│   │   ├── test_health.py    # Multi-component health check tests
│   │   ├── test_sessions.py  # Session & message persistence tests
│   │   ├── test_chat.py      # Grounded RAG chat endpoint tests
│   │   └── test_ship30.py    # Ship 30 skill & artifact endpoint tests
│   ├── Dockerfile            # Backend container definition
│   └── requirements.txt      # Backend pinned dependencies
├── frontend/                 # React UI (Phase 7)
├── scripts/
│   ├── chunker.py            # Token-aware speaker & heading chunker
│   └── ingest.py             # Transcript parser, embedder, and upsert script
├── tests/
│   ├── test_chunker.py       # Chunk size & overlap tests
│   └── test_ingest.py        # Idempotency and parsing tests
├── agent-transcripts/        # Verifiable agent session logs per phase
├── data/
│   └── raw/                  # Downloaded raw transcripts (gitignored)
├── docker-compose.yml        # Multi-container orchestration (postgres, backend)
├── .env.example              # Sample environment configuration
├── requirements.txt          # Root Python dependencies
├── pyproject.toml            # Project metadata and tool configuration
├── ROADMAP.md                # Project roadmap and architectural constraints
├── PRD.md                    # Product requirements document
├── design.md                 # UI/UX and artifact sandbox security spec
└── architecture.md           # Architecture diagrams and system design
```
