# System Architecture — The Lenny Growth Assistant

## 1. High-Level Architecture

```mermaid
flowchart LR
    U[Browser: React Chat + Sandboxed Artifact Viewer] -->|REST / SSE| API[FastAPI Backend]
    API --> ROUTER[LLM Router: Ollama | Free Cloud]
    ROUTER --> OLLAMA[(Local Ollama: Llama 3.2 / Nomic Embed)]
    ROUTER --> CLOUD[(Cloud Provider: Groq / Gemini)]
    API --> RET[Retriever]
    RET --> PG[(Postgres + pgvector\nchunks, sessions, messages, artifacts)]
    INGEST[scripts/ingest.py] --> PG
    RAW[ChatPRD Transcripts Archive] --> INGEST
    API --> ART[Artifact Generator]
    ART --> U
```

---

## 2. Zero-Cost Technology Stack

| Layer | Component | Function |
|---|---|---|
| **Storage & Vectors** | PostgreSQL 16 + `pgvector` | Persistent storage for transcript chunks (vector dimension 768), sessions, messages, and artifacts. |
| **Embeddings** | Ollama (`nomic-embed-text`) | Local 768-dimensional dense vector embeddings; zero API costs. |
| **Local LLM** | Ollama (`llama3.2:3b` / `qwen2.5:7b`) | Offline, local inference engine for chat and skills. |
| **Cloud LLM (Toggle)** | Groq (Llama 3.3) or Google Gemini Flash | Optional free-tier cloud fallback when API keys are provided. |
| **Backend API** | FastAPI (Python 3.11+) | Async REST API, retrieval orchestration, and streaming endpoints. |
| **Frontend** | React + Vite | Clean user interface with conversational stream and artifact panel. |
| **Containerization** | Docker Compose | One-command orchestration for reproducible local deployment. |

---

## 3. Database Schema Specification

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Transcripts & Chunks (Phase 1)
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(768),
    episode_title TEXT,
    guest TEXT,
    source_url TEXT,
    content_hash TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw 
ON chunks USING hnsw (embedding vector_cosine_ops);

-- Chat Sessions (Phase 2 Stub)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Chat Messages (Phase 2 Stub)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Artifacts (Phase 2 Stub)
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Ingestion Pipeline Mechanics
1. **Source Acquisition**: Transcripts downloaded/cloned from `ChatPRD/lennys-podcast-transcripts` to `data/raw/`.
2. **Parsing**: Frontmatter extracted for episode metadata (`title`, `guest`, `date`, `url`); markdown body normalized.
3. **Semantic Chunking**: Transcripts split across headings (`#`, `##`, `###`) and speaker transitions (`Lenny:`, `**Guest:**`) into ~600–800 token segments with ~100 token overlap.
4. **Hashing & Idempotency**: SHA-256 fingerprinting of chunk contents ensuring repeat runs insert 0 duplicate rows.
5. **Local Vectorization**: HTTP calls to Ollama `nomic-embed-text` produce 768-dim vectors.
6. **Batch Upsert**: Bulk insert into Postgres `chunks` table with conflict avoidance.
