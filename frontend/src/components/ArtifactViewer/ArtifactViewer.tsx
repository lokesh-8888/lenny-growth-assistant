import React, { useState, useEffect } from 'react';
import { ArtifactControls } from './ArtifactControls';
import type { ViewTab } from './ArtifactControls';
import { SandboxedIframe } from './SandboxedIframe';
import { MarkdownRenderer } from './MarkdownRenderer';
import { getArtifact } from '../../api/artifacts';
import './artifactViewer.css';

export interface ArtifactData {
  id?: string;
  session_id?: string;
  type: 'ship30' | 'markdown' | 'html' | string;
  title: string;
  content: string;
  word_count?: number;
  citations?: Array<{
    guest?: string;
    episode_title?: string;
    source_url?: string;
  }>;
  created_at?: string;
}

interface ArtifactViewerProps {
  artifact: ArtifactData;
  className?: string;
  onClose?: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({
  artifact,
  className = '',
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<ViewTab>('rendered');
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [content, setContent] = useState<string>(artifact.content || '');

  // Synchronize content or fetch on demand if artifact content was omitted
  useEffect(() => {
    if (artifact.content) {
      setContent(artifact.content);
    } else if (artifact.id) {
      getArtifact(artifact.id)
        .then((full) => {
          if (full?.content) {
            setContent(full.content);
          }
        })
        .catch((err) => {
          console.error('Failed to load artifact content:', err);
        });
    }
  }, [artifact.id, artifact.content]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
    } catch (err) {
      console.error('Failed to copy artifact content:', err);
    }
  };

  const handleDownload = () => {
    const isHtml = artifact.type.toLowerCase() === 'html';
    const extension = isHtml ? 'html' : 'md';
    const mimeType = isHtml ? 'text/html' : 'text/markdown';
    const safeTitle = (artifact.title || 'artifact')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');

    const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${safeTitle}.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const isHtmlType = artifact.type.toLowerCase() === 'html';

  return (
    <div
      className={`artifact-viewer-root ${isFullscreen ? 'fullscreen-mode' : ''} ${className}`}
      data-testid="artifact-viewer"
    >
      <ArtifactControls
        title={artifact.title}
        type={artifact.type}
        wordCount={artifact.word_count}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onCopy={handleCopy}
        onDownload={handleDownload}
        isFullscreen={isFullscreen}
        onToggleFullscreen={() => setIsFullscreen(!isFullscreen)}
        onClose={onClose}
      />

      <div className="artifact-viewport">
        {activeTab === 'rendered' ? (
          <div className="rendered-panel paper-surface" data-testid="rendered-panel">
            {isHtmlType ? (
              <SandboxedIframe content={content} title={artifact.title} />
            ) : (
              <MarkdownRenderer content={content} />
            )}
          </div>
        ) : (
          <div className="source-panel" data-testid="source-panel">
            <div className="source-code-container">
              <pre className="source-code-pre">
                <code>{content}</code>
              </pre>
            </div>
          </div>
        )}
      </div>

      {artifact.citations && artifact.citations.length > 0 && (
        <div className="artifact-footer-citations">
          <span className="citations-label">Grounded sources:</span>
          <div className="citations-list">
            {artifact.citations.map((c, i) => (
              <span key={i} className="citation-pill" title={c.episode_title}>
                {c.guest || 'Lenny Guest'} — {c.episode_title}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
