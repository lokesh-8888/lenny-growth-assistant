# The Lenny Growth Assistant — Zero-Cost Build Roadmap

A phase-by-phase plan for building the full engagement spec (RAG chat + Ship 30/30 skill +
artifact viewer + Docker deployment) using only free tools, free tiers, and free data — designed
to be fed to Antigravity or Codex one phase at a time.

---

## 0. TL;DR — the $0 stack

| Layer | Choice | Why it's free |
|---|---|---|
| Backend API | FastAPI (Python) | Open source |
| Agent/orchestration | Hand-rolled lightweight agent loop (Python), optional Claude Agent SDK wrapper | No paid SDK dependency required; SDK only activates if a key is present |
| Local LLM (mandatory for demo) | Ollama running `llama3.2:3b` or `qwen2.5:7b-instruct-q4_K_M` | Runs on your machine, no API key, no usage cost |
| Cloud LLM (toggle option) | Groq API (Llama 3.x, OpenAI-compatible) **or** Google Gemini free tier | Both have genuinely free API tiers (no card charge) — safer than relying on Anthropic/OpenAI trial credit, which expires |
| Embeddings | Ollama `nomic-embed-text` | Local, free, no key |
| Database + vector store | Postgres + `pgvector` extension, run in Docker Compose locally | No hosted account needed at all; Supabase free tier is a drop-in swap if you want it reachable outside your machine |
| Knowledge base | Free/open Lenny's Podcast transcript archives (below) | No purchase needed |
| Containerization | Docker Compose | Free |
| Frontend | React + Vite, plain CSS or Tailwind | Free |
| Artifact sandbox | `<iframe sandbox>` + DOMPurify | Free client-side libs |
| Repo hosting | GitHub public repo | Free |
| Tests | pytest + Vitest/RTL | Free |
| Build agents | Antigravity and/or Codex CLI | Use free/included usage; treat as pair-programmers, not oracles |

No step in this plan requires a credit card.

---

## 1. Discovery brief (answers PRD requirement #2 — write this into your PRD verbatim, then adjust)

**Primary user:** A PM or growth practitioner at the client company who wants fast, trustworthy
tactical advice without reading through hundreds of hours of podcast transcripts, and without
knowing how to prompt an LLM well.

**Job to be done:** Ask a product/growth question in plain language → get an answer grounded in
real operator interviews, with the source episode identified → optionally turn a useful answer
into a polished, shareable write-up (essay or one-page HTML brief) without doing any editing.

**Pain removed:** Manually searching/skimming transcripts, and the low trust of ungrounded
LLM answers ("this sounds right but where did it come from?").

**Success metric (pick one and track it):**
- Groundedness rate: ≥90% of a 20-question eval set are answered with a correct, verifiable
  citation to a real transcript (rather than an unsupported or hallucinated claim).
- Alternative: median end-to-end response latency under 6s on the local model, under 3s on the
  cloud model, measured across the same eval set.

**Assumptions to record (brief was ambiguous on these — state them explicitly in your PRD):**
- The spec names "Anthropic Claude Agent SDK or Pi Coding Agent" for the agent layer. "Pi Coding
  Agent" isn't a recognized product, so the default here is a small hand-written agent loop
  (retrieval → prompt assembly → generation → citation check), with the Claude Agent SDK wired in
  as an optional backend when `ANTHROPIC_API_KEY` is set. Document this choice in architecture.md.
- "Deploy it locally" is read as: the deliverable is a `docker compose up` that runs entirely on
  the evaluator's machine — not a public cloud deployment.
- No user authentication — single evaluator, one browser session per chat session ID.
- The transcript archive used is one of the free/open repos below, not a paid one, and this is
  called out explicitly in README.md so the evaluator knows the corpus size.

**Scope — in:**
- Grounded RAG chat with session memory and follow-ups
- Ship 30/30 essay-generation skill
- Markdown/HTML artifact generation with a sandboxed in-app viewer
- Local + cloud model toggle with documented fallback
- Docker Compose one-command startup
- Automated tests for retrieval, chat API, and session persistence

**Scope — out (and why):**
- Multi-user auth/accounts — adds complexity with no eval value for a single-evaluator demo
- Scheduled/automatic transcript refresh — replaced with a manual, idempotent `ingest.py --refresh`
  script (still satisfies "refreshed," just not cron-triggered)
- Horizontal scaling / production infra — out of scope for a local forward-deployment demo
- Fine-tuning — retrieval-augmented generation is sufficient and far cheaper

**Risks & trade-offs:**
- *Hallucination* — mitigated with a strict "answer only from retrieved context" system prompt and
  an explicit "not covered in the transcripts" refusal path.
- *Local model quality* — small quantized models reason less reliably; mitigate with tighter
  retrieval (more relevant chunks, less reliance on model reasoning) and a small eval set you
  actually run before submitting.
- *Latency* — CPU-only local inference can be slow; document expected response times per model
  size in README so the evaluator isn't surprised.
- *Data licensing* — only use openly published free transcript archives (below), and cite the
  source repo in README so provenance is clear.
- *Unsafe artifact rendering* — generated HTML is treated as fully untrusted (see §6).
- *Free-tier rate limits* — cloud provider calls can fail on quota; the LLM router must catch this
  and fall back to Ollama automatically, and say so in the UI.

---

## 2. Architecture at a glance

```mermaid
flowchart LR
    U[Browser: React chat + artifact viewer] -->|REST/SSE| API[FastAPI backend]
    API --> ROUTER[LLM Router\nollama | groq | gemini]
    ROUTER --> OLLAMA[(Ollama\nlocal model)]
    ROUTER --> CLOUD[(Free-tier cloud LLM)]
    API --> RET[Retriever]
    RET --> PG[(Postgres + pgvector\nchunks, sessions, messages, artifacts)]
    INGEST[ingest.py] --> PG
    RAW[Free transcript archive] --> INGEST
    API --> ART[Artifact generator]
    ART --> U
```

Everything except the browser and (optionally) the cloud LLM call runs inside Docker on the
evaluator's machine.

---

## 3. Knowledge base — free transcript sources

You need a named, linkable source in README.md. Good free options, largest first:

- **`ChatPRD/lennys-podcast-transcripts`** (GitHub) — 269 full episode transcripts as Markdown
  with YAML frontmatter, one folder per guest, plus a topic index. Fully open, straightforward
  to parse.
- **`evenwing/lennys-data`** / **`LennysNewsletter/lennys-newsletterpodcastdata`** (GitHub) — a
  free "starter pack" of 50 podcast transcripts and 10 newsletter posts in AI-friendly Markdown,
  with an `index.json` of titles/dates/guests. Smaller but very clean if you want a fast build.

Recommendation: start with the starter pack (fast to ingest, good for demoing the pipeline end to
end quickly), then swap the `RAW_DATA_PATH` env var to the 269-episode archive once the pipeline
works, since ingestion is idempotent and provider-agnostic either way.

---

## 4. Phase-by-phase build plan

Work through these in order. Each phase is sized to hand to Antigravity/Codex as one task, with
its own acceptance criteria — commit after each one.

### Phase 0 — Environment & repo skeleton (~2–3 hrs)
- Install Docker Desktop, Ollama, Python 3.11+, Node 20+.
- `ollama pull llama3.2:3b` and `ollama pull nomic-embed-text` (swap for `qwen2.5:7b-instruct-q4_K_M`
  if your machine has 16GB+ RAM and you want better answer quality).
- Create repo structure:
  ```
  /backend        # FastAPI app
  /frontend       # React app
  /scripts        # ingest.py, eval scripts
  /agent-transcripts
  docker-compose.yml
  .env.example
  README.md  PRD.md  design.md  architecture.md
  ```
- **Definition of done:** repo pushed to GitHub, `.env.example` present, nothing secret committed.

### Phase 1 — Data ingestion pipeline
- `scripts/ingest.py`:
  1. Read transcripts from the chosen archive path.
  2. Parse frontmatter (guest, episode title, date, source URL) + body.
  3. Chunk by heading/speaker-turn, ~600–800 tokens with ~100-token overlap.
  4. Embed each chunk via Ollama's `nomic-embed-text`.
  5. Upsert into a `chunks` table (`content`, `embedding vector(768)`, `episode_title`, `guest`,
     `source_url`, `content_hash`).
  6. Make it idempotent: hash each source file; skip re-embedding unchanged files on `--refresh`.
- **Definition of done:** running `python scripts/ingest.py` twice in a row only re-embeds nothing
  the second time, and `select count(*) from chunks` is non-zero.

### Phase 2 — Backend skeleton: sessions & persistence
- FastAPI app with Postgres via SQLAlchemy. Tables: `sessions`, `messages`, `chunks`, `artifacts`.
- Endpoints: `POST /api/sessions`, `GET /api/sessions/{id}/messages`, `GET /health`.
- `/health` checks DB connectivity, Ollama reachability, and whether a cloud key is configured —
  returns per-dependency status, not just one boolean.
- **Definition of done:** creating a session and posting/fetching messages round-trips correctly;
  `/health` correctly reports Ollama as down when it's stopped.

### Phase 3 — LLM configuration layer
- Define one interface (`complete()`, `embed()`) with two-plus implementations: `OllamaProvider`,
  `CloudProvider` (Groq or Gemini, OpenAI-compatible where possible).
- `LLM_PROVIDER` env var selects the default; if the cloud call fails (missing key, timeout,
  rate limit), catch it and transparently retry on Ollama, tagging the response as
  `"served_by": "ollama-fallback"` so the UI can show it.
- Expose current provider/model via `GET /api/config`.
- **Definition of done:** pulling the network cable on the cloud key (unset it) still returns a
  working answer via Ollama, with the fallback flag visible in the API response.

### Phase 4 — Grounded RAG chat endpoint
- `POST /api/chat` → retrieve top-k (5–8) chunks by cosine similarity (`pgvector`'s `<=>`),
  optionally boosted by a simple keyword match on guest/episode name (hybrid retrieval).
- System prompt: answer only from provided chunks; if none pass a similarity threshold, respond
  that the transcripts don't cover this topic instead of guessing.
- Preserve conversation history per session for follow-ups (pass last N turns + fresh retrieval).
- Response includes citations: episode title + guest + source URL for each chunk actually used.
- **Definition of done:** a question with no relevant transcript coverage gets an honest "not
  covered" answer instead of a hallucinated one; a follow-up question ("what about for B2B?")
  correctly uses prior context.

### Phase 5 — Ship 30 for 30 essay skill
- Encode this as a dedicated module (`skills/ship30.py`), not an ad-hoc prompt string, so it's
  reusable and testable:
  - Strong opening hook (question, bold claim, or specific scenario)
  - Clear narrative progression (setup → tension/insight → resolution)
  - Skimmable structure: headings, bullets, selective **bold**
  - One specific, useful, restated takeaway at the end
  - Every non-obvious claim traceable to a retrieved chunk
  - Target ~1,250 words — validate word count post-generation and regenerate/trim if far off
- `POST /api/artifacts/generate` with `type=ship30`, sourced from the current conversation's
  grounded answer(s).
- **Definition of done:** generated essay is within ~10% of 1,250 words, has at least one heading
  and one bullet list, and every specific claim in it maps back to a cited transcript.

### Phase 6 — Artifact generation (Markdown/HTML) + sandboxed viewer
- Same `/api/artifacts/generate` endpoint, `type=markdown` or `type=html`.
- Frontend "Artifact Viewer" panel beside the chat (like Claude's Artifacts): tabs for
  Markdown-rendered view and raw source.
- **Security implementation (see §6 for the write-up you need in design.md):**
  - Render generated HTML inside `<iframe sandbox="allow-scripts">` (deliberately omit
    `allow-same-origin` so the iframe can't read cookies/localStorage or make same-origin requests).
  - Sanitize with DOMPurify before it ever reaches the iframe's `srcdoc`.
  - Add a restrictive CSP meta tag inside the generated document (`default-src 'none'`, only
    `style-src 'unsafe-inline'` and `img-src data:` allowed).
- **Definition of done:** a generated artifact containing `<script>fetch('https://evil.example')</script>`
  cannot make a network call or access parent-page cookies when rendered.

### Phase 7 — Frontend chat UI
- Chat pane (streaming or polling), session switcher ("start new chat"), model/provider indicator
  showing which LLM answered, citations rendered under each answer, artifact viewer pane.
- **Definition of done:** a full flow — new session → ask a question → see cited answer → generate
  a Ship 30 essay → view it in the artifact panel — works without a page reload.

### Phase 8 — Observability & resilience
- Structured JSON logs (request id, session id, provider used, retrieval hit count, latency).
- Graceful handling, each with a clear user-facing message: missing API key, Ollama unreachable,
  empty retrieval results, DB connection failure.
- **Definition of done:** stopping the Postgres container returns a clean 503 with a readable
  error, not a stack trace to the browser.

### Phase 9 — Docker Compose, one-command startup
- Services: `postgres` (pgvector-enabled image), `ollama`, `backend`, `frontend`, plus an `ingest`
  one-off profile (`docker compose run ingest`).
- `.env.example` with every variable documented and safe defaults (local Ollama, no cloud key
  required to boot).
- **Definition of done:** on a clean machine with only Docker + `ollama pull` done, `docker compose
  up` produces a working app with no manual steps.

### Phase 10 — Tests
- Backend: pytest for retrieval correctness (known query → expected chunk), chat endpoint
  contract, session persistence, LLM router fallback behavior (mock the cloud call to fail).
- Frontend: a handful of RTL tests for the chat flow and artifact viewer sandboxing.
- A short manual test plan in README for the two flows that are hard to automate well (RAG answer
  quality, artifact sandbox escape attempts).
- **Definition of done:** `pytest` and the frontend test command both pass in CI or locally with no
  network dependency beyond local Ollama.

### Phase 11 — Documentation deliverables
Write these last, once the system is real, so they describe what was actually built:
- `README.md` — architecture overview, prerequisites, install, env vars, local + cloud model
  setup, run commands, test commands, troubleshooting.
- `PRD.md` — everything from §1 above, refined with real numbers from your eval run.
- `design.md` — UI/UX principles, chat + artifact viewer information architecture, key interaction
  states (loading, error, fallback-provider notice), accessibility notes, and the artifact-viewer
  security write-up.
- `architecture.md` — DB schema, API endpoint list, component boundaries, ingestion/retrieval
  flow, the agent-layer decision (see assumptions above), model toggle design, deployment topology.

### Phase 12 — Agent transcripts, cleanup, submission
- Save your Antigravity/Codex session logs into `/agent-transcripts/`, one file per phase,
  including at least one failed attempt and how you fixed it (this is an explicit deliverable —
  don't only save the clean successes).
- Scrub any secrets/keys from those transcripts before committing.
- Final pass: fresh clone → `docker compose up` → smoke test the full flow once, exactly as an
  evaluator would.

---

## 5. Free LLM/embedding provider notes

| Provider | Free tier reality | Use for |
|---|---|---|
| Ollama | 100% free, local, no key, no rate limit (just your hardware) | Mandatory local demo path |
| Groq | Free API tier, OpenAI-compatible client, fast Llama/Mixtral models | Cloud toggle option |
| Google Gemini | Free tier with real ongoing quota (Flash models) | Alternative cloud toggle |
| Anthropic / OpenAI | Small trial credit only, not free long-term | Fine to wire in as a third option, but don't depend on it for the graded demo |

Architect the router generically (OpenAI-compatible chat interface) so swapping in Anthropic or
OpenAI later is a config change, not a code change — that also satisfies "switch the model without
changing application code" directly.

---

## 6. Security write-up you need for design.md (artifact viewer)

State plainly what the viewer permits and blocks:
- **Permits:** the artifact's own scripts to run inside an isolated frame, for interactivity;
  reading of data: URIs for inline images; inline CSS.
- **Blocks:** any network request from inside the artifact (no `allow-same-origin`, restrictive
  CSP `default-src 'none'`), access to the parent page's cookies/localStorage/DOM, and any raw
  HTML that DOMPurify strips (inline event handlers, `<script src=external>`, etc.) before it's
  even placed in the sandbox.
- **Why this is enough:** the combination of sandbox attributes + CSP + sanitization means a
  worst-case malicious generation can, at most, render broken content inside its own frame — it
  cannot exfiltrate data or affect the rest of the app.

---

## 7. Deliverables checklist

| # | Deliverable | Produced in |
|---|---|---|
| 1 | Public GitHub repo | Phase 0, ongoing |
| 2 | README.md | Phase 11 |
| 3 | PRD.md | §1 + Phase 11 |
| 4 | design.md | §6 + Phase 11 |
| 5 | architecture.md | §2 + Phase 11 |
| 6 | Agent transcripts | Phase 12 |
| 7 | Tests + manual test plan | Phase 10 |

---

## 8. Suggested timeline (solo, using AI coding agents)

| Days | Phases |
|---|---|
| Day 1 | 0–2 |
| Day 2 | 3–4 |
| Day 3 | 5–6 |
| Day 4 | 7–8 |
| Day 5 | 9–10 |
| Day 6 | 11–12, final smoke test |

Compressible to ~3 days if you run phases in parallel across backend/frontend, or if you're
comfortable merging phases 5+6 and 10+11.

---

## 9. Working with Antigravity / Codex

- Feed one phase's "Tasks" + "Definition of done" as the task description per session — not the
  whole roadmap at once. Smaller, checkable diffs are easier to review and to log as transcripts.
- Ask the agent to write the test alongside the code, not after, for anything touching retrieval,
  the LLM router fallback, or the artifact sandbox — these three are the places graders will poke.
- Review every diff yourself before accepting, especially anything touching env/secrets handling
  and the sandbox/CSP config — that's the one place a subtly wrong agent suggestion (e.g. adding
  `allow-same-origin`) silently breaks the security model.
- Commit after each phase with a message referencing the phase number, so your git history and
  `/agent-transcripts` folder tell the same story.
- Export/copy the full session log (including any dead ends) into `/agent-transcripts/phase-N.md`
  before moving to the next phase — easy to forget once you're in flow.
