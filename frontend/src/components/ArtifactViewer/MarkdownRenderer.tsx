import React, { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = '',
}) => {
  const renderedHtml = useMemo(() => {
    if (!content) return '';
    
    // Configure marked for clean, GitHub-flavored output
    marked.setOptions({
      gfm: true,
      breaks: true,
    });

    const raw = marked.parse(content) as string;
    // For markdown, strip any potential scripts completely
    return DOMPurify.sanitize(raw, {
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
      ADD_ATTR: ['target'],
    });
  }, [content]);

  return (
    <div className={`markdown-rendered-body ${className}`}>
      <div
        className="markdown-content"
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
      />
    </div>
  );
};
