import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../../context/ChatContext';
import { Send, Loader2 } from 'lucide-react';

export const ChatInput: React.FC = () => {
  const { sendMessage, isChatLoading } = useChat();
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isChatLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isChatLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isChatLoading) return;
    sendMessage(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto-adjust height up to max 180px
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask a tactical growth question (e.g., 'What are Adam Fishman's 4 growth competencies?')..."
          rows={1}
          disabled={isChatLoading}
          className="chat-textarea"
          data-testid="chat-input-textarea"
        />

        <button
          type="submit"
          disabled={!text.trim() || isChatLoading}
          className="chat-send-btn"
          title="Send question (Enter)"
          aria-label="Send message"
          data-testid="chat-send-button"
        >
          {isChatLoading ? (
            <Loader2 size={16} className="spin-icon" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </div>

      <div className="chat-input-footer">
        <span>Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for a new line</span>
        <span className="groundedness-note">100% Grounded in Lenny's Podcast Transcripts</span>
      </div>
    </form>
  );
};
