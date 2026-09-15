import React from 'react';
import { useModel } from '../../context/ModelContext';
import { useConfig } from '../../context/ConfigContext';
import { ShieldCheck, X, Zap, Cpu, Server, KeyRound } from 'lucide-react';

interface ProviderStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ProviderStatusModal: React.FC<ProviderStatusModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { models } = useModel();
  const { health } = useConfig();

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="provider-status-modal"
        onClick={(e) => e.stopPropagation()}
        data-testid="provider-status-modal"
      >
        <div className="modal-header">
          <div className="modal-header-title">
            <ShieldCheck size={18} className="shield-icon" />
            <h3>Provider Health &amp; Fallback Telemetry</h3>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close provider modal"
          >
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {/* Fallback Guarantee Alert Banner */}
          <div className="resilience-callout-box">
            <Zap size={16} className="callout-icon" />
            <div className="callout-content">
              <strong>Zero-Downtime Resilience Guarantee</strong>
              <p>
                If a cloud model is selected without API credentials, or if the provider
                encounters a rate-limit (HTTP 429) or connection timeout, requests seamlessly
                route to your local Ollama daemon. The answer is flagged with a transparent fallback banner.
              </p>
            </div>
          </div>

          {/* Local Stack Health */}
          <div className="status-section">
            <h4 className="section-title">Local Infrastructure</h4>
            <div className="status-grid">
              <div className="status-card">
                <div className="card-top">
                  <Cpu size={14} />
                  <span>Ollama Local Daemon</span>
                </div>
                <div className="card-val">
                  <span
                    className={`status-dot ${
                      health?.dependencies?.ollama?.status === 'running' ? 'green' : 'amber'
                    }`}
                  />
                  <span>
                    {health?.dependencies?.ollama?.status === 'running'
                      ? 'Connected (Zero-Cost Default)'
                      : 'Offline / Host Local'}
                  </span>
                </div>
              </div>

              <div className="status-card">
                <div className="card-top">
                  <Server size={14} />
                  <span>Postgres 16 + pgvector</span>
                </div>
                <div className="card-val">
                  <span
                    className={`status-dot ${
                      health?.dependencies?.postgres?.status === 'connected' ? 'green' : 'red'
                    }`}
                  />
                  <span>
                    {health?.dependencies?.postgres?.status === 'connected'
                      ? 'Vector Memory Ready'
                      : 'Database Disconnected'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Cloud Keys Status */}
          <div className="status-section">
            <h4 className="section-title">Cloud Provider Credentials</h4>
            <div className="keys-table">
              {models
                .filter((m) => !m.is_local)
                .map((m) => (
                  <div key={m.id} className="key-row">
                    <div className="key-info">
                      <KeyRound size={13} className="key-icon" />
                      <span className="key-name">
                        {m.provider} ({m.name})
                      </span>
                      <code className="key-env">{m.env_key}</code>
                    </div>
                    <div className="key-status">
                      {m.is_available ? (
                        <span className="key-badge configured">Configured</span>
                      ) : (
                        <span className="key-badge unconfigured">
                          Not Set (Ollama Fallback Active)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="modal-done-btn"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
