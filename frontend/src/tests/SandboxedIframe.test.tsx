import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SandboxedIframe } from '../components/ArtifactViewer/SandboxedIframe';

describe('SandboxedIframe Security Component', () => {
  it('renders iframe with strict sandbox attribute omitting allow-same-origin', () => {
    const rawHtml = `
      <!DOCTYPE html>
      <html>
      <head><title>Test Widget</title></head>
      <body><div id="output">Hello</div></body>
      </html>
    `;

    render(<SandboxedIframe content={rawHtml} title="Test Sandbox" />);

    const iframe = screen.getByTitle('Test Sandbox') as HTMLIFrameElement;
    expect(iframe).toBeInTheDocument();

    // 1. Sandbox attribute must include 'allow-scripts'
    expect(iframe.getAttribute('sandbox')).toContain('allow-scripts');

    // 2. Sandbox attribute MUST strictly OMIT 'allow-same-origin'
    expect(iframe.getAttribute('sandbox')).not.toContain('allow-same-origin');

    // 3. Sandbox attribute must omit other dangerous capabilities
    expect(iframe.getAttribute('sandbox')).not.toContain('allow-top-navigation');
    expect(iframe.getAttribute('sandbox')).not.toContain('allow-modals');
  });

  it('injects restrictive Content-Security-Policy into iframe srcDoc', () => {
    const rawHtml = '<h1>Interactive ROI</h1>';
    render(<SandboxedIframe content={rawHtml} title="CSP Verification" />);

    const iframe = screen.getByTitle('CSP Verification') as HTMLIFrameElement;
    const srcDoc = iframe.getAttribute('srcdoc') || '';

    expect(srcDoc).toContain('Content-Security-Policy');
    expect(srcDoc).toContain("default-src 'none'");
    expect(srcDoc).toContain("style-src 'unsafe-inline'");
    expect(srcDoc).toContain("script-src 'unsafe-inline'");
  });
});
