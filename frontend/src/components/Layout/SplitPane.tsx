import React from 'react';

interface SplitPaneProps {
  sidebar: React.ReactNode;
  isSidebarOpen: boolean;
  chat: React.ReactNode;
  viewer: React.ReactNode;
  isViewerOpen: boolean;
}

export const SplitPane: React.FC<SplitPaneProps> = ({
  sidebar,
  isSidebarOpen,
  chat,
  viewer,
  isViewerOpen,
}) => {
  return (
    <div className="split-pane-layout">
      {/* Collapsible Sidebar */}
      <aside className={`split-sidebar ${isSidebarOpen ? 'open' : 'closed'}`} aria-label="Chat Sessions">
        {sidebar}
      </aside>

      {/* Main Workspace: Chat + Artifact Viewer */}
      <div className={`split-workspace ${isViewerOpen ? 'dual-pane' : 'single-pane'}`}>
        {/* Chat Pane */}
        <section className="chat-pane" aria-label="Conversation Stream">
          {chat}
        </section>

        {/* Artifact Viewer Pane (Rendered if artifact is active and open) */}
        {isViewerOpen && (
          <section className="artifact-pane" aria-label="Sandboxed Artifact Viewer">
            {viewer}
          </section>
        )}
      </div>
    </div>
  );
};
