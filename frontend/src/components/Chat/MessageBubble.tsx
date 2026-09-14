import React from 'react';
import type { MessageItem } from '../../api/sessions';
import { MarkdownRenderer } from '../ArtifactViewer/MarkdownRenderer';
import { CitationCard } from './CitationCard';
import { ArtifactActionToolbar } from './ArtifactActionToolbar';
import { Bot, User, AlertTriangle } from 'lucide-react';

interface MessageBubbleProps {
  message: MessageItem;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isFallback = message.served_by === 'ollama-fallback';

  return (
    <div
      className={`message-row ${isUser ? 'user-row' : 'assistant-row'}`}
      data-testid={`message-bubble-${message.role}`}
    >
      <div className="message-avatar">
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-meta-header">
          <span className="message-author">{isUser ? 'You' : 'Lenny Growth Assistant'}</span>

          {!isUser && message.served_by && (
            <div className="message-served-tag">
              {isFallback ? (
                <span className="served-fallback" title="Served via local Ollama after cloud rate limit">
                  <AlertTriangle size={11} />
                  <span>Ollama Fallback</span>
                </span>
              ) : (
                <span className="served-normal">
                  {message.served_by}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="message-bubble-body">
          {isUser ? (
            <p className="user-message-text">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} className="assistant-markdown" />
          )}
        </div>

        {/* Assistant Citations & Quick Action Triggers */}
        {!isUser && (
          <div className="assistant-extras">
            {message.citations && message.citations.length > 0 && (
              <CitationCard citations={message.citations} />
            )}

            <ArtifactActionToolbar messageId={message.id} />
          </div>
        )}
      </div>
    </div>
  );
};
