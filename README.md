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

---

## LLM Configuration & Zero-Downtime Fallback

The assistant incorporates a provider-agnostic LLM routing architecture:
1. **Local Mode (`LLM_PROVIDER=ollama`)**:
   - Queries local Ollama instance on `http://localhost:11434` (model: `llama3.2:3b`).
   - Responses are tagged with `"served_by": "ollama"`.
2. **Cloud Mode (`LLM_PROVIDER=cloud`)**:
   - Routes requests to free-tier cloud providers via OpenAI-compatible endpoints (Groq `llama-3.3-70b-versatile` or Gemini `gemini-1.5-flash`).
   - Responses are tagged with `"served_by": "groq"` or `"served_by": "gemini"`.
3. **Resilient Auto-Fallback**:
   - If the cloud provider encounters any failure (missing/invalid API key, 401 unauthenticated, 429 rate limit, 5xx server error, or network timeout), the `LLMRouter` catches the error, logs a structured warning, immediately dispatches the request to local Ollama, and tags the response with `"served_by": "ollama-fallback"`.
   - The caller **never** receives an unhandled error due to cloud provider instability.

---

## Running Automated Tests

Run pytest across the entire test suite (data ingestion, chunker, health checks, and session persistence):
```bash
pytest -v
```

Tests verify:
1. **Chunking Accuracy**: Validates token boundaries (600–800 tokens), overlap (~100 tokens), and speaker turn parsing.
2. **Ingestion Idempotency**: Verifies that re-running ingestion against unchanged transcripts inserts 0 new database records.
3. **Session Lifecycle**: Create session -> add messages -> retrieve in chronological order -> cascade delete.
4. **Health Check Resiliency**: Validates live checks and mocks for healthy, degraded, and database-down states.

---

## Project Structure

```
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── config.py         # Pydantic settings
│   │   ├── database.py       # SQLAlchemy engine & session factory
│   │   ├── models.py         # SQLAlchemy ORM models (sessions, messages, chunks, artifacts)
│   │   ├── schemas.py        # Pydantic validation & serialization schemas
│   │   ├── routers/
│   │   │   ├── health.py     # Multi-component /health endpoint
│   │   │   └── sessions.py   # Sessions & messages REST endpoints
│   │   └── main.py           # FastAPI entrypoint, CORS, exception handlers
│   ├── db/
│   │   ├── init.sql          # Postgres extension initialization
│   │   └── schema.sql        # Tables: chunks, sessions, messages, artifacts
│   ├── tests/
│   │   ├── conftest.py       # Test fixtures and database setup
│   │   ├── test_health.py    # Multi-component health check tests
│   │   └── test_sessions.py  # Session & message persistence tests
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
