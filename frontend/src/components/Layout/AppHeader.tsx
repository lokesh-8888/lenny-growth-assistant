import React from 'react';
import { useConfig } from '../../context/ConfigContext';
import { useChat } from '../../context/ChatContext';
import { Cpu, AlertTriangle, CheckCircle2, XCircle, Menu, Layers } from 'lucide-react';

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
  const { config, health } = useConfig();
  const { activeArtifact } = useChat();

  const isFallback = config?.current_provider === 'ollama-fallback';

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
        {/* Fallback warning alert pill if cloud failed */}
        {isFallback ? (
          <div className="model-pill fallback-alert" data-testid="fallback-telemetry-badge">
            <AlertTriangle size={13} className="alert-icon" />
            <span>⚡ Cloud Rate-Limited — Served via Ollama Fallback</span>
          </div>
        ) : (
          <div className="model-pill normal" data-testid="model-telemetry-badge">
            <Cpu size={13} />
            <span>
              {config?.current_provider === 'ollama' ? 'Ollama' : (config?.current_provider || 'Local')}:{' '}
              <strong>{config?.current_model || 'llama3.1:8b'}</strong>
            </span>
          </div>
        )}

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
