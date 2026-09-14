/**
 * DOMPurify configuration and CSP enforcement for sandboxed artifact rendering.
 * Enforces the non-negotiable three-layer defense:
 * 1. DOMPurify sanitization
 * 2. Mandatory restrictive Content Security Policy (CSP)
 * 3. Iframe sandbox with 'allow-scripts' only (no 'allow-same-origin')
 */

import DOMPurify from 'dompurify';

export const MANDATORY_CSP_META = 
  '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; script-src \'unsafe-inline\';">';

/**
 * Strips external script references (<script src="...">) so only self-contained
 * inline scripts can execute inside the sandbox.
 */
export function stripExternalScripts(html: string): string {
  // Matches <script ... src=... >...</script> or self-closing <script ... src=... />
  return html.replace(/<script\b[^>]*\bsrc\s*=[^>]*>([\s\S]*?)<\/script>/gi, '')
             .replace(/<script\b[^>]*\bsrc\s*=[^>]*\/>/gi, '');
}

/**
 * Ensures the restrictive Content Security Policy meta tag is injected inside <head>.
 */
export function injectCspMeta(html: string): string {
  // If CSP is already present, do not duplicate
  if (/<meta[^>]+http-equiv=["']Content-Security-Policy["']/i.test(html)) {
    return html;
  }

  // Inject into <head>
  if (/<head\b[^>]*>/i.test(html)) {
    return html.replace(/(<head\b[^>]*>)/i, `$1\n    ${MANDATORY_CSP_META}`);
  }

  // Inject into <html>
  if (/<html\b[^>]*>/i.test(html)) {
    return html.replace(/(<html\b[^>]*>)/i, `$1\n<head>\n    ${MANDATORY_CSP_META}\n</head>`);
  }

  // If no html tags, wrap with minimal standard skeleton
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    ${MANDATORY_CSP_META}
    <title>Growth Artifact</title>
</head>
<body>
${html}
</body>
</html>`;
}

/**
 * Sanitizes untrusted HTML for the sandboxed iframe.
 * Permits inline styles and safe inline scripts for calculators, but blocks
 * external script sources, external fonts/iframes, and dangerous attributes.
 */
export function sanitizeArtifactHtml(rawHtml: string): string {
  if (!rawHtml || typeof rawHtml !== 'string') {
    return '';
  }

  // 1. First defense: Strip external script inclusions
  const withoutExternalScripts = stripExternalScripts(rawHtml);

  // 2. DOMPurify pass: Allow HTML5 elements, inline styles, and safe inline scripts
  // DOMPurify in browser environment
  const cleanHtml = DOMPurify.sanitize(withoutExternalScripts, {
    WHOLE_DOCUMENT: true,
    ADD_TAGS: ['style', 'script', 'title', 'meta', 'head', 'body', 'html'],
    ADD_ATTR: [
      'id', 'class', 'style', 'type', 'name', 'value', 'min', 'max',
      'step', 'placeholder', 'for', 'rows', 'cols', 'disabled', 'checked',
      'http-equiv', 'content', 'charset'
    ],
    FORBID_TAGS: ['iframe', 'frame', 'object', 'embed', 'base', 'link', 'applet'],
    FORBID_ATTR: ['target'], // Prevent target="_top" or target="_parent"
    ALLOW_DATA_ATTR: true,
  });

  // 3. Guarantee CSP meta tag in document head
  return injectCspMeta(cleanHtml);
}
