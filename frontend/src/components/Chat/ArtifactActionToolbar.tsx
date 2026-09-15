import React from 'react';
import { useChat } from '../../context/ChatContext';
import { Sparkles, FileText, Code2, Loader2 } from 'lucide-react';

interface ArtifactActionToolbarProps {
  messageId: string;
}

export const ArtifactActionToolbar: React.FC<ArtifactActionToolbarProps> = ({ messageId }) => {
  const { generateArtifactAction, isArtifactGenerating, generatingType } = useChat();

  const handleGenerate = (type: 'ship30' | 'markdown' | 'html') => {
    generateArtifactAction(type, undefined, messageId);
  };

  return (
    <div className="message-artifact-actions" data-testid="artifact-actions-toolbar">
      <span className="actions-prompt-label">Create artifact:</span>

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
            <Sparkles size={12} />
          )}
          <span>Ship 30 Essay</span>
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
            <FileText size={12} />
          )}
          <span>Executive Brief</span>
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
          <span>HTML Widget</span>
        </button>
      </div>
    </div>
  );
};
