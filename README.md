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

## Quickstart (One-Command Docker Compose)

The entire Lenny Growth Assistant stack runs with a single command via Docker Compose. No external cloud API keys or manual installations are required.

### 1. Prerequisites
- **Docker Desktop** installed and running.
- **Ollama** running locally on host (`http://localhost:11434`) with the embedding model:
  ```bash
  ollama pull nomic-embed-text
  ```

### 2. Configure Environment (Optional)
Copy the template configuration:
```bash
cp .env.example .env
```
All defaults connect automatically to host Ollama (`http://host.docker.internal:11434`) and local PostgreSQL.

### 3. Launch Services
Start all services in detached mode:
```bash
docker compose up -d
```

Compose automatically initializes:
- **`lenny_postgres`**: PostgreSQL 16 with `pgvector` extension and persistent storage (`postgres_data` named volume).
- **`lenny_backend`**: FastAPI asynchronous backend running as a secure non-root user (`appuser`, UID 10001) with internal healthchecks.
- **`lenny_frontend`**: Production React + Vite SPA served via Nginx with reverse-proxying for `/api/` and `/health`, and dual-port exposure.

### 4. Service Endpoints & Verification
| Service | URL | Notes |
| :--- | :--- | :--- |
| **Frontend UI** | `http://localhost` or `http://localhost:5173` | Production React SPA with dual-pane chat & sandboxed artifact viewer |
| **Nginx Health Proxy** | `http://localhost/health` | Multi-component health check proxied to FastAPI backend |
| **FastAPI Backend (Direct)** | `http://localhost:8000` | Direct backend API server |
| **Interactive API Docs** | `http://localhost:8000/docs` | Swagger / OpenAPI 3.1 documentation |
| **PostgreSQL 16** | `localhost:5432` | Vector database (`postgres` user / `lenny_growth` DB) |

Check container health status:
```bash
docker compose ps
```

Verify the health endpoint:
```bash
curl http://localhost/health
```

### 5. Run Data Ingestion (Docker Container)
Run the ingestion pipeline in a dedicated batch container without installing local Python dependencies:
```bash
# Ingest first 5 episodes (rapid smoke test):
docker compose run --rm ingest python scripts/ingest.py --limit 5

# Full archive ingestion (only new or changed transcripts):
docker compose run --rm ingest python scripts/ingest.py --refresh
```

### 6. Data Persistence & Teardown
Postgres data and vector embeddings persist across container stops and restarts via the `postgres_data` Docker volume:
```bash
# Stop containers (preserves database volume):
docker compose down

# Stop and delete database volume (fresh start):
docker compose down -v
```

---

## Local Development (Outside Docker)

If developing locally on host machine:

### 1. Database
Start only the PostgreSQL container:
```bash
docker compose up -d postgres
```

### 2. Python Backend
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 3. Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### 4. Host Ingestion Pipeline
```bash
python scripts/ingest.py --limit 5
```

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

### Observability, Structured Logging & Outage Resilience (Phase 8)

The backend incorporates zero-cost, enterprise-grade structured observability and outage resilience:

#### 1. Structured JSON Logging
All backend logs are emitted as single-line JSON records to stdout (`LOG_FORMAT=json`):
```json
{
  "timestamp": "2026-09-15T02:23:45Z",
  "level": "INFO",
  "logger": "app.services.rag.agent",
  "message": "RAG completion finished (1162.5ms) served by ollama",
  "request_id": "b3c6a7e2-4821-4b3f-9171-84197e889d12",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "event": "rag_completion_success",
  "provider": "ollama",
  "served_by": "ollama",
  "model": "llama3.1:8b",
  "retrieval_hits": 5,
  "top_similarity_score": 0.8241,
  "retrieval_latency_ms": 42.1,
  "llm_latency_ms": 1120.4,
  "total_latency_ms": 1162.5,
  "is_grounded": true
}
```
- Context variables (`contextvars`) automatically bind `request_id` and `session_id` to every asynchronous execution frame without manual parameter drilling.

#### 2. Request Tracing Middleware
- Injects or preserves `X-Request-ID` (UUID) across all logs and response headers.
- Emits `X-Response-Time-Ms` showing total round-trip processing duration.
- Emits structured `http_request_finished` logs with HTTP method, path, status, and latency.

#### 3. Standardized Error Envelopes (Zero Stack Trace Leakage)
The backend guarantees that raw stack traces, database credentials, and internal SQL statements are **never** leaked to clients:
```json
{
  "error": {
    "code": "DATABASE_UNAVAILABLE",
    "message": "The database is currently unreachable. Please ensure the PostgreSQL container is running.",
    "request_id": "b3c6a7e2-4821-4b3f-9171-84197e889d12",
    "status_code": 503
  },
  "detail": "The database is currently unreachable. Please ensure the PostgreSQL container is running."
}
```

| Error Code | HTTP Status | Trigger Condition | Operator Guidance |
|---|---|---|---|
| `DATABASE_UNAVAILABLE` | 503 | Postgres container offline or pool exhausted | Verify `docker compose up -d postgres` is healthy. |
| `OLLAMA_UNAVAILABLE` | 503 | Ollama daemon offline on port 11434 | Run `ollama serve` or ensure Ollama is running locally. |
| `INFERENCE_FAILED` | 502 | Both primary cloud and fallback Ollama fail | Check network connection or verify local model weights. |
| `SESSION_NOT_FOUND` | 404 | Session UUID does not exist | Create a new session via `POST /api/sessions`. |
| `VALIDATION_ERROR` | 422 | Invalid payload or missing fields | Check input format against Swagger documentation. |
| `INTERNAL_SERVER_ERROR`| 500 | Unhandled internal exception | Stack trace logged internally with `request_id`; safe envelope returned to user. |

---

## Running Automated Tests

### Backend Test Suite (pytest)
Run pytest across the entire backend test suite (ingestion, retrieval, health, sessions, RAG chat, Ship 30, multi-type artifacts, and resilience):
```bash
# In project root:
pytest -v
# Or using the local virtualenv:
.venv\Scripts\pytest -v
```
All 72 backend tests pass across ingestion, retrieval, health, chat, artifacts, and outage resilience.

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
