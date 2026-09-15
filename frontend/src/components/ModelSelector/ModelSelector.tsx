import React, { useState, useRef, useEffect } from 'react';
import { useModel } from '../../context/ModelContext';
import { useConfig } from '../../context/ConfigContext';
import type { ModelItem } from '../../api/models';
import {
  ChevronDown,
  Check,
  Info,
  AlertCircle,
  Server,
  Zap,
  ShieldCheck,
  X,
  KeyRound,
  Cpu,
} from 'lucide-react';
import './ModelSelector.css';

export const ModelSelector: React.FC = () => {
  const {
    models,
    selectedModelId,
    selectedModel,
    setSelectedModelId,
    isStatusModalOpen,
    setIsStatusModalOpen,
  } = useModel();

  const { health } = useConfig();

  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
        setIsStatusModalOpen(false);
      }
    };

    if (isOpen || isStatusModalOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isStatusModalOpen, setIsStatusModalOpen]);

  const handleSelect = (model: ModelItem) => {
    setSelectedModelId(model.id);
    setIsOpen(false);
  };

  const getBadgeClass = (badge: string) => {
    const lower = badge.toLowerCase();
    if (lower.includes('fast') && !lower.includes('ultra')) return 'badge-fast';
    if (lower.includes('ultra')) return 'badge-ultra';
    if (lower.includes('quality')) return 'badge-quality';
    if (lower.includes('reasoning')) return 'badge-reasoning';
    return 'badge-default';
  };

  const activeName = selectedModel?.name || 'Llama 3.2 (3B)';
  const activeProvider = selectedModel?.provider || 'Ollama';

  return (
    <div className="model-selector-container" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        className={`model-selector-trigger ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select active AI model"
        data-testid="model-selector-trigger"
      >
        <span className="trigger-status-indicator" />
        <span className="trigger-model-name">{activeName}</span>
        <span className="trigger-provider-pill">{activeProvider}</span>
        <ChevronDown size={14} className={`trigger-chevron ${isOpen ? 'rotated' : ''}`} />
      </button>

      {/* Popover Menu */}
      {isOpen && (
        <div
          className="model-popover-menu"
          role="listbox"
          aria-label="Available models"
          data-testid="model-popover-menu"
        >
          <div className="popover-header">
            <span className="popover-title">Model</span>
            <span className="popover-subtitle">
              {models.length} models • Zero-cost default
            </span>
          </div>

          <div className="model-items-list">
            {models.map((model) => {
              const isSelected = model.id === selectedModelId;
              const isUnconfiguredCloud = !model.is_local && !model.is_available;

              return (
                <div
                  key={model.id}
                  role="option"
                  aria-selected={isSelected}
                  className={`model-item-row ${isSelected ? 'selected' : ''} ${
                    isUnconfiguredCloud ? 'unconfigured' : ''
                  }`}
                  onClick={() => handleSelect(model)}
                  data-testid={`model-option-${model.id}`}
                >
                  <div className="model-item-left">
                    <div className="selection-check-slot">
                      {isSelected ? (
                        <Check size={14} className="check-icon" data-testid="selected-check-icon" />
                      ) : (
                        <span className="empty-check" />
                      )}
                    </div>

                    <div className="model-name-group">
                      <div className="model-name-line">
                        <span className="model-name-text">{model.name}</span>
                        <span className="model-tier-tag">{model.tier}</span>
                      </div>
                      <span className="model-provider-sub">{model.provider}</span>
                    </div>
                  </div>

                  <div className="model-item-right">
                    {/* Performance badge */}
                    <span className={`pill-badge ${getBadgeClass(model.badge)}`}>
                      {model.badge}
                    </span>

                    {/* Unconfigured Warning Pill */}
                    {isUnconfiguredCloud && (
                      <div
                        className="warning-pill"
                        title={`Set ${model.env_key} to enable (routes to Ollama fallback if selected)`}
                      >
                        <AlertCircle size={12} />
                        <span>Key missing</span>
                      </div>
                    )}

                    {/* Info tooltip trigger */}
                    <div className="info-icon-wrapper" onClick={(e) => e.stopPropagation()}>
                      <Info size={13} className="info-icon" />
                      <div className="info-tooltip">
                        <p className="tooltip-desc">{model.description}</p>
                        <div className="tooltip-meta">
                          <span>Context window: <strong>{model.context_window}</strong></span>
                          {model.env_key && (
                            <span>Env: <code>{model.env_key}</code></span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="popover-divider" />

          {/* Footer Action */}
          <button
            type="button"
            className="popover-footer-btn"
            onClick={() => {
              setIsOpen(false);
              setIsStatusModalOpen(true);
            }}
            data-testid="view-provider-status-btn"
          >
            <div className="footer-btn-content">
              <Zap size={13} className="zap-icon" />
              <span>View Provider Status &amp; Fallback Info</span>
            </div>
            <span className="footer-arrow">&rsaquo;</span>
          </button>
        </div>
      )}

      {/* Provider Status Modal / Drawer */}
      {isStatusModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsStatusModalOpen(false)}>
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
                onClick={() => setIsStatusModalOpen(false)}
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
                      <span className={`status-dot ${health?.dependencies?.ollama?.status === 'running' ? 'green' : 'amber'}`} />
                      <span>{health?.dependencies?.ollama?.status === 'running' ? 'Connected (Zero-Cost Default)' : 'Offline / Host Local'}</span>
                    </div>
                  </div>

                  <div className="status-card">
                    <div className="card-top">
                      <Server size={14} />
                      <span>Postgres 16 + pgvector</span>
                    </div>
                    <div className="card-val">
                      <span className={`status-dot ${health?.dependencies?.postgres?.status === 'connected' ? 'green' : 'red'}`} />
                      <span>{health?.dependencies?.postgres?.status === 'connected' ? 'Vector Memory Ready' : 'Database Disconnected'}</span>
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
                          <span className="key-name">{m.provider} ({m.name})</span>
                          <code className="key-env">{m.env_key}</code>
                        </div>
                        <div className="key-status">
                          {m.is_available ? (
                            <span className="key-badge configured">Configured</span>
                          ) : (
                            <span className="key-badge unconfigured">Not Set (Ollama Fallback Active)</span>
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
                onClick={() => setIsStatusModalOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
