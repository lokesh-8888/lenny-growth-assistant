# The Lenny Growth Assistant

A local-first, zero-cost AI Growth and Product Assistant grounded in 260+ episodes of **Lenny's Podcast**. Ask tactical questions and receive answers cited directly from experienced operators, or generate structured growth frameworks and Ship 30/30 essays.

---

## Zero-Cost Stack

- **Storage**: PostgreSQL 16 with `pgvector` running locally via Docker Compose.
- **Embeddings**: Local Ollama running `nomic-embed-text` (768-dimensional embeddings, 100% free, no API key).
- **LLM**: Local Ollama (`llama3.2:3b` or `qwen2.5:7b-instruct`) with optional free cloud fallback (Groq / Gemini free tiers).
- **Knowledge Base**: Curated transcripts from [`ChatPRD/lennys-podcast-transcripts`](https://github.com/ChatPRD/lennys-podcast-transcripts) (269 Markdown transcripts with YAML frontmatter).
- **Backend / Orchestration**: FastAPI (Python 3.11+) hand-rolled retrieval & persistence loop.

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

## Quickstart (Phase 1: Ingestion)

### 1. Configure Environment
Copy the example environment file:
```bash
cp .env.example .env
```
All defaults are configured for seamless local operation out of the box.

### 2. Start PostgreSQL with pgvector
Start the database container:
```bash
docker compose up -d postgres
```
This initializes PostgreSQL on port `5432` and runs `CREATE EXTENSION IF NOT EXISTS vector;` on first boot.

### 3. Install Python Dependencies
Create a virtual environment and install requirements:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
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

## Running Automated Tests

Run pytest across the test suite:
```bash
pytest -v
```
Tests verify:
1. **Chunking Accuracy**: Validates token boundaries (600–800 tokens), overlap (~100 tokens), and speaker turn parsing.
2. **Idempotency**: Verifies that re-running ingestion against unchanged transcripts inserts 0 new database records.

---

## Project Structure

```
lenny-growth-assistant/
├── backend/
│   └── db/
│       ├── init.sql          # Postgres extension initialization
│       └── schema.sql        # Tables: chunks, sessions, messages, artifacts
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
├── docker-compose.yml        # Docker Compose configuration
├── .env.example              # Sample environment configuration
├── requirements.txt          # Pinned Python dependencies
├── pyproject.toml            # Project metadata and tool configuration
├── ROADMAP.md                # Project roadmap and architectural constraints
├── PRD.md                    # Product requirements document
├── design.md                 # UI/UX and artifact sandbox security spec
└── architecture.md           # Architecture diagrams and system design
```
