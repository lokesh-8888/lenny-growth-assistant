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

## 3. Security Specification: Sandboxed Artifact Viewer

Generated HTML and scripts are treated as completely untrusted content. The artifact viewer employs defense-in-depth isolation:

### Permissions & Capabilities
- **Permits**:
  - Isolated script execution strictly within the sandboxed iframe for UI interactivity (e.g. interactive charts, tabs, filters).
  - Inline CSS styles.
  - Safe data URIs for inline imagery (`data:image/...`).

### Restrictions & Boundaries
- **Blocks**:
  - Network requests from within the artifact frame (no API calls, no analytics beacons).
  - Access to parent page DOM, cookies, local storage, or session tokens.
  - Same-origin privilege escalation (the iframe deliberately omits `allow-same-origin`).
  - Loading external unverified scripts or stylesheets.

### Defense-in-Depth Layers
1. **DOMPurify Sanitization**: All generated HTML is cleaned client-side prior to rendering, stripping dangerous attributes (`onload`, `<script src="...">`, event handlers).
2. **Iframe Sandboxing**: Rendered via `<iframe sandbox="allow-scripts">` without `allow-same-origin`.
3. **Content Security Policy (CSP)**: Generated documents inject a restrictive CSP meta tag:
   ```html
   <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'unsafe-inline';">
   ```
This guarantees that even a worst-case malicious payload cannot leak evaluator data or access host browser resources.
