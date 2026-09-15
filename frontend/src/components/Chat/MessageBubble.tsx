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
  const servedBy = message.served_by || '';
  const isFallback = servedBy.toLowerCase().includes('ollama-fallback');

  const formatServedBy = (raw: string) => {
    if (raw === 'ollama-fallback') {
      return 'Ollama Fallback';
    }
    if (raw.toLowerCase().includes('ollama-fallback')) {
      const match = raw.match(/requested:\s*([^)]+)/i);
      let label = 'Cloud Model';
      if (match && match[1]) {
        const req = match[1].trim();
        if (req.includes('claude')) label = 'Claude 3.5';
        else if (req.includes('gemini')) label = 'Gemini 1.5 Flash';
        else if (req.includes('gpt-4o')) label = 'GPT-4o Mini';
        else if (req.includes('groq') || req.includes('70b')) label = 'Groq Llama 3.3 (70B)';
        else label = req;
      }
      return `⚠️ Requested ${label} (Key Missing) — Served via Local Ollama Fallback`;
    }

    if (raw === 'ollama:llama3.2:3b' || raw === 'llama3.2:3b' || raw === 'ollama') {
      return '🟢 Llama 3.2 3B (Local)';
    }
    if (raw === 'ollama:llama3.1:8b') {
      return '🟢 Llama 3.1 8B (Local)';
    }
    if (raw === 'google:gemini-1.5-flash') {
      return '🟢 Gemini 1.5 Flash';
    }
    if (raw === 'groq:llama-3.3-70b-versatile') {
      return '🟢 Groq Llama 3.3 (70B)';
    }
    if (raw === 'anthropic:claude-3-5-sonnet') {
      return '🟢 Claude 3.5 Sonnet';
    }
    if (raw === 'openai:gpt-4o-mini') {
      return '🟢 GPT-4o Mini';
    }

    return raw;
  };

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
                <span
                  className="served-fallback"
                  title="Served via local Ollama after cloud rate limit"
                  data-testid="message-fallback-badge"
                >
                  <AlertTriangle size={11} />
                  <span>{formatServedBy(message.served_by)}</span>
                </span>
              ) : (
                <span className="served-normal" data-testid="message-model-badge">
                  {formatServedBy(message.served_by)}
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
