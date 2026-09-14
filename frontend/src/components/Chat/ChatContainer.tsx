import React, { useEffect, useRef } from 'react';
import { useChat } from '../../context/ChatContext';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { Sparkles, AlertCircle, X, Compass, Loader2 } from 'lucide-react';

const STARTER_PROMPTS = [
  {
    title: 'Growth Team Competencies',
    query: 'What are Adam Fishman\'s 4 core competencies for building a high-performing growth team?',
  },
  {
    title: 'Product-Led Growth Loops',
    query: 'How does Elena Verna define B2B Product-Led Growth loops vs traditional marketing funnels?',
  },
  {
    title: 'Overcoming Cold Start',
    query: 'What specific tactics did early Airbnb and marketplace founders use to overcome the cold-start problem?',
  },
  {
    title: 'CAC Payback Benchmarks',
    query: 'What are the healthy CAC payback benchmarks across consumer and B2B SaaS according to Lenny\'s guests?',
  },
];

export const ChatContainer: React.FC = () => {
  const { messages, isChatLoading, error, clearError, sendMessage } = useChat();
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message
  useEffect(() => {
    if (typeof scrollAnchorRef.current?.scrollIntoView === 'function') {
      scrollAnchorRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isChatLoading]);

  return (
    <div className="chat-container-root">
      {/* Error Banner */}
      {error && (
        <div className="chat-error-banner" data-testid="chat-error-banner">
          <div className="error-content">
            <AlertCircle size={16} className="error-icon" />
            <span>{error}</span>
          </div>
          <button onClick={clearError} className="error-dismiss-btn" aria-label="Dismiss error">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Message Stream */}
      <div className="chat-stream" role="log" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty-state" data-testid="chat-empty-state">
            <div className="empty-hero-icon">
              <Sparkles size={32} />
            </div>
            <h2 className="empty-title">What growth challenge are you tackling?</h2>
            <p className="empty-desc">
              Ask tactical product & growth questions answered exclusively from 260+ interviews with top operators like Adam Fishman, Elena Verna, Brian Balfour, and more.
            </p>

            <div className="starter-grid">
              <div className="starter-header">
                <Compass size={14} />
                <span>Suggested Operator Queries:</span>
              </div>
              <div className="starter-cards">
                {STARTER_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    className="starter-card-btn"
                    onClick={() => sendMessage(item.query)}
                    data-testid={`starter-prompt-${idx}`}
                  >
                    <span className="starter-card-title">{item.title}</span>
                    <span className="starter-card-query">"{item.query}"</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {isChatLoading && (
              <div className="assistant-loading-indicator" data-testid="chat-loading-indicator">
                <Loader2 size={16} className="spin-icon" />
                <span>Retrieving podcast excerpts & synthesizing answer...</span>
              </div>
            )}
          </div>
        )}
        <div ref={scrollAnchorRef} />
      </div>

      {/* Input Form at Bottom */}
      <div className="chat-input-sticky">
        <ChatInput />
      </div>
    </div>
  );
};
