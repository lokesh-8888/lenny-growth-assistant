import { describe, it, expect } from 'vitest';
import { sanitizeArtifactHtml, stripExternalScripts, injectCspMeta, MANDATORY_CSP_META } from '../utils/sanitize';

describe('Artifact HTML Sanitization & CSP Enforcement', () => {
  it('strips external script tags with remote src attributes', () => {
    const malicious = `
      <div>
        <h2>Growth Calculator</h2>
        <script src="https://evil.example.com/exfiltrate.js"></script>
        <script src="http://attacker.com/cookie-stealer.js">alert(1);</script>
        <script>const safeCalculation = 42;</script>
      </div>
    `;
    const stripped = stripExternalScripts(malicious);
    expect(stripped).not.toContain('evil.example.com');
    expect(stripped).not.toContain('attacker.com');
    expect(stripped).toContain('const safeCalculation = 42;');
  });

  it('guarantees restrictive Content-Security-Policy meta tag in head', () => {
    const html = '<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>';
    const secured = injectCspMeta(html);
    expect(secured).toContain(MANDATORY_CSP_META);
    expect(secured).toContain("default-src 'none'");
    expect(secured).toContain("style-src 'unsafe-inline'");
    expect(secured).toContain("script-src 'unsafe-inline'");
    expect(secured).toContain("img-src data:");

    // Ensure it does not duplicate CSP if already present
    const again = injectCspMeta(secured);
    expect(again.match(/Content-Security-Policy/g)?.length).toBe(1);
  });

  it('wraps bare HTML fragments with full document containing CSP', () => {
    const fragment = '<div class="metric-card"><span>Payback</span></div>';
    const secured = injectCspMeta(fragment);
    expect(secured).toContain('<!DOCTYPE html>');
    expect(secured).toContain('<head>');
    expect(secured).toContain(MANDATORY_CSP_META);
    expect(secured).toContain(fragment);
  });

  it('full sanitizeArtifactHtml strips forbidden iframes and targets while keeping inline styling and scripts', () => {
    const dirty = `
      <!DOCTYPE html>
      <html>
      <head><title>Test</title></head>
      <body>
        <style>body { background: #000; }</style>
        <a href="https://example.com" target="_top">Click me</a>
        <iframe src="https://evil.com"></iframe>
        <script src="https://evil.com/hook.js"></script>
        <script>
          const val = 100;
        </script>
      </body>
      </html>
    `;
    const clean = sanitizeArtifactHtml(dirty);
    expect(clean).not.toContain('<iframe');
    expect(clean).not.toContain('target="_top"');
    expect(clean).not.toContain('evil.com/hook.js');
    expect(clean).toContain('Content-Security-Policy');
    expect(clean).toContain('const val = 100;');
    expect(clean).toContain('background: #000;');
  });
});
