import React, { useState } from 'react';
import type { CitationItem } from '../../api/sessions';
import { ExternalLink, ChevronDown, ChevronUp, Clock, Quote } from 'lucide-react';

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
          {citations.map((c, i) => {
            const quoteText = c.quote_snippet || c.quote;
            const timestampText = c.timestamp || '00:00';

            return (
              <div key={i} className="citation-entry" data-testid="citation-entry">
                <div className="citation-header">
                  <div className="citation-guest-wrap">
                    <span className="citation-mic-icon" aria-hidden="true">🎙️</span>
                    <span className="citation-guest">{c.guest || 'Lenny Podcast Guest'}</span>
                    {c.timestamp && (
                      <span className="citation-timestamp-badge" title={`Timestamp: ${timestampText}`}>
                        <Clock size={10} className="ts-clock-icon" />
                        <span>[{timestampText}]</span>
                      </span>
                    )}
                  </div>
                  {c.source_url && (
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="citation-link"
                      title="View original episode transcript or video"
                    >
                      <span>Transcript</span>
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>

                <div className="citation-episode" title={c.episode_title}>
                  {c.episode_title || 'Episode archive'}
                </div>

                {quoteText && (
                  <div className="citation-quote-box" data-testid="citation-quote-box">
                    <Quote size={10} className="quote-glyph" />
                    <span className="citation-quote-text">"{quoteText}"</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
