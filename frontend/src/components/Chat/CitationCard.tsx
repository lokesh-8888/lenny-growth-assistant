import React, { useState } from 'react';
import type { CitationItem } from '../../api/sessions';
import { BookOpen, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

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
        <BookOpen size={14} className="citation-book-icon" />
        <span>
          {citations.length} Grounded {citations.length === 1 ? 'Source' : 'Sources'} Cited
        </span>
        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
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
                    <ExternalLink size={11} />
                  </a>
                )}
              </div>
              <div className="citation-episode" title={c.episode_title}>
                {c.episode_title || 'Episode Archive'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
