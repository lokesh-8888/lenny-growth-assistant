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

export interface ArtifactControlsProps {
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

export const ArtifactControls: React.FC<ArtifactControlsProps> = ({
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
    <div className="artifact-toolbar-wrapper" data-testid="artifact-toolbar">
      {/* Top Document Header */}
      <div className="artifact-header-identity">
        <span className={`artifact-badge ${badge.className}`}>
          {badge.icon}
          <span>{badge.label}</span>
        </span>
        <h3 className="artifact-title" title={title}>
          {title}
        </h3>
      </div>

      {/* Main Flex Toolbar with Defined Slots: [tabs] ... [word count] [Isolated Sandbox] [Copy] [Download] [expand] [close] */}
      <div className="artifact-toolbar">
        {/* Slot 1: Tabs */}
        <div className="toolbar-tabs-slot" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === 'rendered'}
            className={`tab-btn ${activeTab === 'rendered' ? 'active' : ''}`}
            onClick={() => onTabChange('rendered')}
            title="Switch to rendered document"
          >
            <Eye size={13} />
            <span>Rendered View</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'source'}
            className={`tab-btn ${activeTab === 'source' ? 'active' : ''}`}
            onClick={() => onTabChange('source')}
            title="Switch to raw source code"
          >
            <Code size={13} />
            <span>Raw Source</span>
          </button>
        </div>

        {/* Spacer */}
        <div className="toolbar-spacer" />

        {/* Action Slots */}
        <div className="toolbar-actions-slot">
          {/* Slot 2: Word Count */}
          {wordCount !== undefined && wordCount > 0 && (
            <span className="artifact-word-count">
              {wordCount.toLocaleString()} words
            </span>
          )}

          {/* Slot 3: Isolated Sandbox Badge */}
          {type === 'html' && (
            <div
              className="sandbox-security-tag"
              title="Strict CSP 'default-src none' + opaque iframe sandbox active"
            >
              <ShieldCheck size={13} className="shield-icon" />
              <span>Isolated Sandbox</span>
            </div>
          )}

          {/* Slot 4: Copy Button */}
          <button
            className="toolbar-action-btn"
            onClick={handleCopyClick}
            title="Copy raw artifact source"
            aria-label="Copy source code"
          >
            {copied ? <Check size={13} className="text-moss" /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {/* Slot 5: Download Button */}
          <button
            className="toolbar-action-btn"
            onClick={onDownload}
            title={`Download .${type === 'html' ? 'html' : 'md'}`}
            aria-label="Download artifact file"
          >
            <Download size={13} />
            <span>Download</span>
          </button>

          {/* Slot 6: Fullscreen Toggle */}
          <button
            className="toolbar-action-btn icon-only"
            onClick={onToggleFullscreen}
            title={isFullscreen ? 'Exit full screen' : 'Expand full screen'}
            aria-label={isFullscreen ? 'Exit full screen' : 'Full screen'}
          >
            {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>

          {/* Slot 7: Close Button */}
          {onClose && (
            <button
              className="toolbar-action-btn icon-only close-artifact-btn"
              onClick={onClose}
              title="Close viewer"
              aria-label="Close artifact viewer"
              data-testid="close-artifact-btn"
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
