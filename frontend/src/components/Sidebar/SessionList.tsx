import React, { useState } from 'react';
import { useChat } from '../../context/ChatContext';
import { Plus, MessageSquare, Trash2, Search } from 'lucide-react';

export const SessionList: React.FC = () => {
  const {
    sessions,
    activeSessionId,
    startNewChat,
    selectSession,
    removeSession,
  } = useChat();

  const [searchFilter, setSearchFilter] = useState('');

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (window.confirm('Delete this conversation session and all its artifacts?')) {
      removeSession(sessionId);
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <div className="session-list-container">
      <div className="sidebar-header">
        <button
          className="new-chat-btn"
          onClick={startNewChat}
          data-testid="new-chat-button"
        >
          <Plus size={16} />
          <span>New Chat</span>
        </button>
      </div>

      {sessions.length > 5 && (
        <div className="session-search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Search past chats..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="search-input"
          />
        </div>
      )}

      <div className="sessions-scroll" role="list">
        {filteredSessions.length === 0 ? (
          <div className="empty-sessions">
            <MessageSquare size={24} className="empty-icon" />
            <p>{searchFilter ? 'No matching chats' : 'No chats yet'}</p>
            <span>Start a consultation above</span>
          </div>
        ) : (
          filteredSessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <div
                key={session.id}
                role="listitem"
                className={`session-item ${isActive ? 'active' : ''}`}
                onClick={() => selectSession(session.id)}
                data-testid={`session-item-${session.id}`}
              >
                <div className="session-item-icon">
                  <MessageSquare size={15} />
                </div>
                <div className="session-item-body">
                  <span className="session-item-title" title={session.title}>
                    {session.title || 'Untitled Consultation'}
                  </span>
                  <div className="session-item-meta">
                    <span className="session-date">{formatDate(session.updated_at || session.created_at)}</span>
                    {session.message_count !== undefined && session.message_count > 0 && (
                      <span className="session-msg-badge">{session.message_count} msgs</span>
                    )}
                  </div>
                </div>
                <button
                  className="delete-session-btn"
                  onClick={(e) => handleDelete(e, session.id)}
                  title="Delete chat session"
                  aria-label="Delete session"
                  data-testid={`delete-session-${session.id}`}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
