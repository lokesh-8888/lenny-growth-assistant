import React, { useMemo } from 'react';
import { sanitizeArtifactHtml } from '../../utils/sanitize';

interface SandboxedIframeProps {
  content: string;
  title?: string;
  className?: string;
}

export const SandboxedIframe: React.FC<SandboxedIframeProps> = ({
  content,
  title = 'Sandboxed Artifact Output',
  className = '',
}) => {
  // Sanitize and inject restrictive CSP
  const sanitizedSrcDoc = useMemo(() => {
    return sanitizeArtifactHtml(content);
  }, [content]);

  return (
    <div className={`sandboxed-iframe-container ${className}`}>
      <iframe
        // SECURITY CRITICAL:
        // 1. "allow-scripts" enables isolated JavaScript for internal calculations
        // 2. Deliberately OMIT "allow-same-origin" so iframe has opaque origin (null)
        // 3. Omitting allow-same-origin blocks parent DOM, cookies, and localStorage access
        sandbox="allow-scripts"
        srcDoc={sanitizedSrcDoc}
        title={title}
        className="sandboxed-iframe"
        aria-label={title}
      />
    </div>
  );
};
