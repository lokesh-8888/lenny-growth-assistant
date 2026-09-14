import React, { useState } from 'react';
import {
  Code,
  Eye,
  Copy,
  Check,
  Download,
  Maximize2,
  Minimize2,
  ShieldCheck,
  FileText,
  Sparkles,
  X,
} from 'lucide-react';

export type ViewTab = 'rendered' | 'source';

interface ArtifactToolbarProps {
  title: string;
  type: string;
  wordCount?: number;
  activeTab: ViewTab;
  onTabChange: (tab: ViewTab) => void;
  onCopy: () => void;
  onDownload: () => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  onClose?: () => void;
}

export const ArtifactToolbar: React.FC<ArtifactToolbarProps> = ({
  title,
  type,
  wordCount,
  activeTab,
  onTabChange,
  onCopy,
  onDownload,
  isFullscreen,
  onToggleFullscreen,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyClick = () => {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getTypeBadge = () => {
    switch (type.toLowerCase()) {
      case 'ship30':
        return { label: 'Ship 30/30 Essay', icon: <Sparkles size={13} />, className: 'badge-ship30' };
      case 'html':
        return { label: 'Interactive HTML', icon: <Code size={13} />, className: 'badge-html' };
      case 'markdown':
      default:
        return { label: 'Executive Brief', icon: <FileText size={13} />, className: 'badge-markdown' };
    }
  };

  const badge = getTypeBadge();

  return (
    <div className="artifact-toolbar">
      <div className="toolbar-left">
        <div className={`artifact-badge ${badge.className}`}>
          {badge.icon}
          <span>{badge.label}</span>
        </div>
        <h3 className="artifact-title" title={title}>
          {title}
        </h3>
        {wordCount !== undefined && wordCount > 0 && (
          <span className="artifact-word-count">
            {wordCount.toLocaleString()} {type === 'html' ? 'words' : 'words'}
          </span>
        )}
      </div>

      <div className="toolbar-center">
        <div className="view-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === 'rendered'}
            className={`tab-btn ${activeTab === 'rendered' ? 'active' : ''}`}
            onClick={() => onTabChange('rendered')}
            title="Switch to Rendered Output"
          >
            <Eye size={15} />
            <span>Rendered</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'source'}
            className={`tab-btn ${activeTab === 'source' ? 'active' : ''}`}
            onClick={() => onTabChange('source')}
            title="Switch to Raw Code/Markdown"
          >
            <Code size={15} />
            <span>Raw Source</span>
          </button>
        </div>
      </div>

      <div className="toolbar-right">
        {type === 'html' && (
          <div className="sandbox-security-tag" title="Strict CSP 'default-src none' + opaque iframe sandbox active">
            <ShieldCheck size={14} className="shield-icon" />
            <span>Isolated Sandbox</span>
          </div>
        )}

        <button
          className="toolbar-action-btn"
          onClick={handleCopyClick}
          title="Copy raw artifact source"
          aria-label="Copy source code"
        >
          {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>

        <button
          className="toolbar-action-btn"
          onClick={onDownload}
          title={`Download .${type === 'html' ? 'html' : 'md'}`}
          aria-label="Download artifact file"
        >
          <Download size={16} />
          <span>Download</span>
        </button>

        <button
          className="toolbar-action-btn icon-only"
          onClick={onToggleFullscreen}
          title={isFullscreen ? 'Exit full screen' : 'Expand full screen'}
          aria-label={isFullscreen ? 'Exit full screen' : 'Full screen'}
        >
          {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>

        {onClose && (
          <button
            className="toolbar-action-btn icon-only close-artifact-btn"
            onClick={onClose}
            title="Close viewer"
            aria-label="Close artifact viewer"
            data-testid="close-artifact-btn"
          >
            <X size={16} />
          </button>
        )}
      </div>
    </div>
  );
};
