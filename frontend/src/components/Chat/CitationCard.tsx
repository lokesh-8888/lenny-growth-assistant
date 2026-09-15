import React, { useState } from 'react';
import type { CitationItem } from '../../api/sessions';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

interface CitationCardProps {
  citations: CitationItem[];
}

export const CitationCard: React.FC<CitationCardProps> = ({ citations }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="citations-container" data-testid="citation-container">
      <button
        className="citations-toggle-btn"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        title="Toggle grounded transcript citations"
      >
        <span className="citation-grounded-indicator" aria-hidden="true" />
        <span className="citation-count-text">
          {citations.length} grounded {citations.length === 1 ? 'source' : 'sources'} cited
        </span>
        {isExpanded ? <ChevronUp size={12} className="chevron-icon" /> : <ChevronDown size={12} className="chevron-icon" />}
      </button>

      {isExpanded && (
        <div className="citations-expanded-list">
          {citations.map((c, i) => (
            <div key={i} className="citation-entry" data-testid="citation-entry">
              <div className="citation-header">
                <span className="citation-guest">{c.guest || 'Lenny Podcast Guest'}</span>
                {c.source_url && (
                  <a
                    href={c.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="citation-link"
                    title="View original episode transcript"
                  >
                    <span>Transcript</span>
                    <ExternalLink size={10} />
                  </a>
                )}
              </div>
              <div className="citation-episode" title={c.episode_title}>
                {c.episode_title || 'Episode archive'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
