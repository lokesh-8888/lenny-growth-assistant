# Design & UI/UX Specification — The Lenny Growth Assistant

## 1. Overview
The Lenny Growth Assistant interface combines conversational AI search with an interactive Artifact Viewer workspace. The design prioritizes speed, clarity, citation transparency, and operator utility.

---

## 2. Information Architecture

1. **Sidebar / Session Switcher**:
   - Create new chat session.
   - List historical sessions stored locally in PostgreSQL.
   - Model indicator showing the active LLM provider (Ollama local vs. Cloud toggle).
2. **Central Chat Stream**:
   - Message bubbles with streaming tokens.
   - Grounded citations beneath assistant responses: Episode Title, Guest Name, and Source URL.
   - Direct action triggers: "Generate Ship 30/30 Essay", "Export as Markdown Brief", "View as HTML".
3. **Right Artifact Viewer Panel**:
   - Side-by-side inspection view (similar to Claude Artifacts).
   - Tabs: Preview (Rendered HTML/Markdown), Raw Source Code, Copy/Export buttons.

---

## 3. UI/UX Principles & Dual-View Workspaces

- **Operator-Grade Aesthetics**: Sleek dark mode (`#090d16` base, `#111827` surface), glassmorphic headers with `backdrop-filter: blur(12px)`, and system typography.
- **Dual-View Tabs**: Seamless switching between high-fidelity Rendered view and raw syntax-highlighted source view without losing state or scrolling position.
- **Micro-Interactions**: Instant visual feedback for copying source code, downloading `.html`/`.md` files, and toggling fullscreen view.
- **Visual Provenance**: Footer citation pills linking assertions back to specific guests and episodes.

---

## 4. Key Interaction States

1. **Initial / Empty State**: Helpful onboarding prompt inviting the user to ask a growth question.
2. **Generating / Streaming State**: Smooth loading indicators and progress spinners.
3. **Refined / Validated State**: Displaying artifact badges (`Ship 30 Essay`, `Executive Brief`, `Interactive HTML`) with word counts and security indicators.
4. **Fallback Notice**: Visual indicator whenever responses are served via local fallback (`served_by: "ollama-fallback"`).

---

## 5. Information Architecture & Component Hierarchy

```
App
├── Header (Brand Logo, Navigation, Artifact Type Filter Pills)
└── ArtifactViewer
    ├── ArtifactToolbar
    │   ├── Left (Type Badge, Artifact Title, Word Count)
    │   ├── Center (View Tabs: Rendered / Raw Source)
    │   └── Right (Sandbox Security Indicator, Copy, Download, Fullscreen)
    ├── Viewport
    │   ├── Rendered Panel
    │   │   ├── SandboxedIframe (for type="html")
    │   │   └── MarkdownRenderer (for type="markdown" | "ship30")
    │   └── Source Panel (<pre><code> with monospaced code)
    └── Footer (Grounded Sources & Citation Badges)
```

---

## 6. Security Specification: Sandboxed Artifact Viewer (Non-Negotiable §6)

All generated HTML and client-side code are treated as **completely untrusted**. To protect the host application, parent DOM, authentication cookies, and evaluator data, the Artifact Viewer enforces an unbypassable three-layer defense:

### What the Viewer Permits
- **Isolated Script Execution**: The artifact's own scripts run exclusively inside an isolated frame to power interactive calculators (e.g. CAC/LTV sliders, growth loop simulators).
- **Inline CSS**: Self-contained `<style>` blocks for rich, responsive UI styling.
- **Data URIs**: Reading safe `data:image/...` URIs for inline charts and imagery.

### What the Viewer Blocks
- **External Network Requests**: Any `fetch()`, `XMLHttpRequest`, WebSocket, `navigator.sendBeacon()`, or external asset load is strictly blocked by CSP (`default-src 'none'`).
- **Parent DOM & Cookie Access**: The iframe runs under an opaque/null origin because `allow-same-origin` is deliberately omitted. Any attempt to read `window.parent.document` or `window.parent.document.cookie` throws a cross-origin SecurityError.
- **Parent Navigation & Frame Busting**: The iframe strictly omits `allow-top-navigation`, preventing any untrusted script from redirecting the parent window.
- **External Script Inclusion**: DOMPurify pre-strips `<script src="...">` tags, guaranteeing that only audited inline code can exist.
- **Form Submissions & Popups**: Deliberately omits `allow-forms` and `allow-popups` to block phishing or external window spawning.

### Defense-in-Depth Matrix

| Layer | Implementation | Security Boundary Enforced | Threat Mitigated |
|---|---|---|---|
| **Layer 1: Pre-Render Sanitization** | `DOMPurify.sanitize(...)` with custom filter in `frontend/src/utils/sanitize.ts` | Strips `<script src="...">`, `<iframe>`, `<object>`, `<embed>`, and `target="_top"`. | Prevents remote code execution (RCE) and external script harvesting. |
| **Layer 2: Content Security Policy (CSP)** | `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';">` injected into `<head>` | Blocks all outbound socket, HTTP, and beacon traffic. | Prevents data exfiltration and external beaconing. |
| **Layer 3: Browser Iframe Sandboxing** | `<iframe sandbox="allow-scripts" srcdoc="...">` (strictly **no** `allow-same-origin`) | Enforces an opaque/unique origin (`null`). | Prevents parent DOM access, cookie theft, and localStorage tampering. |

### Why This Is Enough
The combination of sandbox attributes + restrictive CSP + pre-sanitization guarantees that a worst-case malicious payload can, at most, render broken content inside its own isolated frame. It cannot exfiltrate data, communicate over the network, or tamper with the parent application.

