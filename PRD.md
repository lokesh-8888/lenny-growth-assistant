# Product Requirements Document (PRD) — The Lenny Growth Assistant

## 1. Overview & Problem Statement
A product manager or growth practitioner needs fast, trustworthy, and tactical advice grounded in real operator experience without manually skimming through hundreds of hours of podcast transcripts or relying on ungrounded, hallucinated generic LLM answers.

**The Lenny Growth Assistant** is an AI assistant powered by retrieval-augmented generation (RAG) over Lenny's Podcast transcripts archive. It answers tactical product and growth questions with verified episode citations and enables turning insights into structured artifacts (such as Ship 30/30 essays or one-page HTML briefs).

---

## 2. Discovery Brief & User Persona

- **Primary User**: Product managers, growth leads, founders, and operators seeking battle-tested frameworks from top tech leaders.
- **Job to Be Done**: Ask a product or growth question in natural language → receive an answer strictly grounded in operator interviews with episode and guest citations → optionally generate polished, shareable artifacts.
- **Pain Removed**: Skimming hours of audio/transcripts, dealing with hallucinatory LLM claims, and formatting research notes manually.
- **Success Metric**:
  - **Groundedness Rate**: $\ge 90\%$ of eval questions answered with accurate, verifiable citations to actual transcripts.
  - **Latency**: Median end-to-end response time under 6s on local models (Ollama), under 3s on free cloud tiers (Groq/Gemini).

---

## 3. Scope

### In-Scope (Phase 1 through Completion)
- **Phase 1 (Current)**:
  - Containerized PostgreSQL with `pgvector` extension.
  - Ingestion pipeline parsing 269 podcast transcripts from `ChatPRD/lennys-podcast-transcripts`.
  - Speaker-turn and heading chunking (~600–800 tokens with ~100-token overlap).
  - Local embedding generation via Ollama `nomic-embed-text` (768 dimensions).
  - Source file SHA-256 hashing for idempotent execution and `--refresh` support.
  - Automated tests for chunking logic and ingestion idempotency.
- **Future Phases (Phases 2–12)**:
  - FastAPI session management and chat persistence (`sessions`, `messages`, `artifacts`).
  - Provider-agnostic LLM router (Ollama local fallback with cloud toggle).
  - Grounded RAG retrieval with hybrid search and citation linking.
  - Ship 30/30 essay generation skill (~1,250 words structured format).
  - Sandboxed artifact viewer with strict CSP and DOMPurify sanitization.
  - React + Vite chat interface.

### Out-of-Scope
- Paid API keys / credit-card services (strictly zero-cost stack).
- Multi-user authentication & enterprise RBAC (single-evaluator focus).
- Automatic cron-based transcript scraping (manual idempotent `--refresh` fulfills needs).
- Model fine-tuning (RAG provides sufficient accuracy at zero training cost).

---

## 4. Key Constraints
- **Zero-Cost Stack**: Purely open-source and free tools (FastAPI, React, Ollama, Postgres/pgvector, Docker Compose).
- **Offline Capable**: Primary execution runs fully local via Ollama (`nomic-embed-text` and `llama3.2:3b`).
- **Provenance**: Transcript corpus sourced openly from GitHub repository `ChatPRD/lennys-podcast-transcripts`.
