import React from 'react';
import { useConfig } from '../../context/ConfigContext';
import { useChat } from '../../context/ChatContext';
import { AlertTriangle, CheckCircle2, XCircle, Menu, Layers } from 'lucide-react';
import { ModelSelector } from '../ModelSelector';

interface AppHeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isViewerOpen: boolean;
  onToggleViewer: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar,
  isViewerOpen,
  onToggleViewer,
}) => {
  const { health } = useConfig();
  const { activeArtifact } = useChat();

  const getHealthDot = () => {
    const status = health?.status;
    if (status === 'healthy') {
      return (
        <span className="health-badge healthy" title="All systems operational (Postgres & Ollama connected)">
          <CheckCircle2 size={12} />
          <span>Healthy</span>
        </span>
      );
    }
    if (status === 'degraded') {
      return (
        <span className="health-badge degraded" title="System degraded: Ollama or DB experiencing issues">
          <AlertTriangle size={12} />
          <span>Degraded</span>
        </span>
      );
    }
    return (
      <span className="health-badge unhealthy" title="Backend service disconnected">
        <XCircle size={12} />
        <span>Offline</span>
      </span>
    );
  };

  return (
    <header className="app-main-header">
      <div className="header-left">
        <button
          className="icon-btn mobile-menu-btn"
          onClick={onToggleSidebar}
          aria-label={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
          title="Toggle sessions sidebar"
        >
          <Menu size={18} />
        </button>

        <div className="brand-badge">
          <div className="brand-icon">LG</div>
          <div className="brand-text">
            <h1 className="brand-heading">The Lenny Growth Assistant</h1>
            <span className="brand-sub">Grounded in 260+ Operator Transcripts</span>
          </div>
        </div>
      </div>

      <div className="header-right">
        {/* Interactive Model Selector Popover */}
        <ModelSelector />

        {/* Health status dot */}
        {getHealthDot()}

        {/* Toggle Viewer button if artifact exists */}
        {activeArtifact && (
          <button
            className={`viewer-toggle-btn ${isViewerOpen ? 'active' : ''}`}
            onClick={onToggleViewer}
            title={isViewerOpen ? 'Hide Artifact Viewer' : 'Show Artifact Viewer'}
            aria-label="Toggle artifact viewer"
          >
            <Layers size={15} />
            <span>{isViewerOpen ? 'Hide Artifact' : 'View Artifact'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
