import React from 'react';
import { useChat } from '../../context/ChatContext';
import { Code2, Loader2 } from 'lucide-react';

export interface QuickActionsProps {
  messageId: string;
}

export const QuickActions: React.FC<QuickActionsProps> = ({ messageId }) => {
  let generateArtifactAction = (_type: 'ship30' | 'markdown' | 'html', _title?: string, _messageId?: string) => {};
  let isArtifactGenerating = false;
  let generatingType: string | null = null;

  try {
    const chat = useChat();
    generateArtifactAction = chat.generateArtifactAction;
    isArtifactGenerating = chat.isArtifactGenerating;
    generatingType = chat.generatingType;
  } catch {
    // Resilient fallback when component is rendered in isolated test
  }

  const handleGenerate = (type: 'ship30' | 'markdown' | 'html') => {
    generateArtifactAction(type, undefined, messageId);
  };

  return (
    <div className="message-artifact-actions" data-testid="artifact-actions-toolbar">
      <span className="actions-prompt-label">Synthesize:</span>

      <div className="artifact-action-buttons">
        <button
          className={`artifact-trigger-btn ${generatingType === 'ship30' ? 'loading' : ''}`}
          onClick={() => handleGenerate('ship30')}
          disabled={isArtifactGenerating}
          title="Generate a ~1,250-word Ship 30 for 30 essay based on this answer"
          data-testid="generate-ship30-btn"
        >
          {generatingType === 'ship30' ? (
            <Loader2 size={12} className="spin-icon" />
          ) : (
            <span className="btn-action-icon">✍️</span>
          )}
          <span>Turn into Ship 30 Essay</span>
        </button>

        <button
          className={`artifact-trigger-btn ${generatingType === 'markdown' ? 'loading' : ''}`}
          onClick={() => handleGenerate('markdown')}
          disabled={isArtifactGenerating}
          title="Generate an executive teardown and checklist"
          data-testid="generate-markdown-btn"
        >
          {generatingType === 'markdown' ? (
            <Loader2 size={12} className="spin-icon" />
          ) : (
            <span className="btn-action-icon">📊</span>
          )}
          <span>Generate Brief</span>
        </button>

        <button
          className={`artifact-trigger-btn ${generatingType === 'html' ? 'loading' : ''}`}
          onClick={() => handleGenerate('html')}
          disabled={isArtifactGenerating}
          title="Generate an interactive standalone HTML calculator or framework widget"
          data-testid="generate-html-btn"
        >
          {generatingType === 'html' ? (
            <Loader2 size={12} className="spin-icon" />
          ) : (
            <Code2 size={12} />
          )}
          <span>Interactive Widget</span>
        </button>
      </div>
    </div>
  );
};
