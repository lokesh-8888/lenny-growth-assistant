import React, { useState, useEffect } from 'react';
import { useConfig } from '../../context/ConfigContext';
import { useChat } from '../../context/ChatContext';
import { AlertTriangle, CheckCircle2, XCircle, Menu, Layers, Sun, Moon } from 'lucide-react';
import { ModelDropdown } from '../ModelSelector/ModelDropdown';

export interface HeaderProps {
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  isViewerOpen: boolean;
  onToggleViewer: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isSidebarOpen,
  onToggleSidebar,
  isViewerOpen,
  onToggleViewer,
}) => {
  const { health } = useConfig();
  const { activeArtifact } = useChat();
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

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
        <ModelDropdown />

        {/* Theme Toggle Button */}
        <button
          className="theme-toggle-btn icon-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label="Toggle theme"
          data-testid="theme-toggle-btn"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Health status badge */}
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
