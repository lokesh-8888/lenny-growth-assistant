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

export const DEFAULT_SANDBOX_BASE_CSS = `
<style id="sandbox-base-styles">
  html, body {
    margin: 0;
    padding: 20px;
    background-color: #14171F;
    color: #EDF0F5;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.5;
  }
  * { box-sizing: border-box; }
</style>
`;

/**
 * Strips markdown code fences (```html ... ```) if the model output wrapped the HTML.
 */
export function stripMarkdownFences(raw: string): string {
  if (!raw) return '';
  let cleaned = raw.trim();
  if (cleaned.startsWith('```html')) {
    cleaned = cleaned.replace(/^```html\s*/i, '');
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```\s*/, '');
  }
  if (cleaned.endsWith('```')) {
    cleaned = cleaned.replace(/\s*```$/, '');
  }
  return cleaned.trim();
}

/**
 * Strips external script references (<script src="...">) so only self-contained
 * inline scripts can execute inside the sandbox.
 */
export function stripExternalScripts(html: string): string {
  return html.replace(/<script\b[^>]*\bsrc\s*=[^>]*>([\s\S]*?)<\/script>/gi, '')
             .replace(/<script\b[^>]*\bsrc\s*=[^>]*\/>/gi, '');
}

/**
 * Ensures the restrictive Content Security Policy meta tag and base dark theme styling
 * are injected inside <head>.
 */
export function injectCspMeta(html: string): string {
  const hasCsp = /<meta[^>]+http-equiv=["']Content-Security-Policy["']/i.test(html);
  const cspTag = hasCsp ? '' : `${MANDATORY_CSP_META}\n`;

  // Inject into <head>
  if (/<head\b[^>]*>/i.test(html)) {
    return html.replace(/(<head\b[^>]*>)/i, `$1\n    ${cspTag}    ${DEFAULT_SANDBOX_BASE_CSS}`);
  }

  // Inject into <html>
  if (/<html\b[^>]*>/i.test(html)) {
    return html.replace(/(<html\b[^>]*>)/i, `$1\n<head>\n    ${cspTag}    ${DEFAULT_SANDBOX_BASE_CSS}\n</head>`);
  }

  // If no html tags, wrap with minimal standard skeleton
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    ${MANDATORY_CSP_META}
    ${DEFAULT_SANDBOX_BASE_CSS}
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

  // 1. Strip markdown fences if present
  const unFenced = stripMarkdownFences(rawHtml);

  // 2. Strip external script inclusions
  const withoutExternalScripts = stripExternalScripts(unFenced);

  // 3. DOMPurify pass: Allow HTML5 elements, inline styles, and safe inline scripts
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

  // 4. Guarantee CSP meta tag and base styles in document head
  return injectCspMeta(cleanHtml);
}
