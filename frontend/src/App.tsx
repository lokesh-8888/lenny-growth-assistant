import React, { useState, useEffect } from 'react';
import { ConfigProvider } from './context/ConfigContext';
import { ModelProvider } from './context/ModelContext';
import { ChatProvider, useChat } from './context/ChatContext';
import { Header } from './components/Layout/Header';
import { SplitPane } from './components/Layout/SplitPane';
import { SessionHistory } from './components/Sidebar/SessionHistory';
import { ModelSelector } from './components/Sidebar/ModelSelector';
import { ChatContainer } from './components/Chat/ChatContainer';
import { ArtifactViewer } from './components/ArtifactViewer';
import './App.css';

const MainLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const { activeArtifact, closeArtifact } = useChat();

  // Automatically open the artifact pane whenever a new artifact is set
  useEffect(() => {
    if (activeArtifact) {
      setIsViewerOpen(true);
    }
  }, [activeArtifact]);

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const toggleViewer = () => setIsViewerOpen((prev) => !prev);

  const handleCloseViewer = () => {
    setIsViewerOpen(false);
    closeArtifact();
  };

  return (
    <div className="app-container">
      <Header
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={toggleSidebar}
        isViewerOpen={isViewerOpen && !!activeArtifact}
        onToggleViewer={toggleViewer}
      />

      <main className="app-main">
        <SplitPane
          sidebar={
            <div className="sidebar-inner">
              <SessionHistory />
              <ModelSelector />
            </div>
          }
          isSidebarOpen={isSidebarOpen}
          chat={<ChatContainer />}
          viewer={
            activeArtifact ? (
              <ArtifactViewer artifact={activeArtifact} onClose={handleCloseViewer} />
            ) : null
          }
          isViewerOpen={isViewerOpen && !!activeArtifact}
        />
      </main>
    </div>
  );
};

export function App() {
  return (
    <ConfigProvider>
      <ModelProvider>
        <ChatProvider>
          <MainLayout />
        </ChatProvider>
      </ModelProvider>
    </ConfigProvider>
  );
}

export default App;
