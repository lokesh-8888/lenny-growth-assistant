import React, { useState, useRef, useEffect } from 'react';
import { useModel } from '../../context/ModelContext';
import type { ModelItem } from '../../api/models';
import {
  ChevronDown,
  Check,
  Info,
  AlertCircle,
  Zap,
  Cpu,
  Cloud,
} from 'lucide-react';
import { ProviderStatusModal } from './ProviderStatusModal';
import './ModelSelector.css';

export const ModelDropdown: React.FC = () => {
  const {
    models,
    selectedModelId,
    selectedModel,
    setSelectedModelId,
    isStatusModalOpen,
    setIsStatusModalOpen,
  } = useModel();

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
    if (lower.includes('reasoning') || lower.includes('thinking')) return 'badge-reasoning';
    return 'badge-default';
  };

  const activeName = selectedModel?.name || 'Llama 3.2 (3B)';
  const activeProvider = selectedModel?.provider || 'Ollama';
  const isLocalActive = selectedModel?.is_local ?? true;

  const localModels = models.filter((m) => m.is_local);
  const cloudModels = models.filter((m) => !m.is_local);

  const renderModelRow = (model: ModelItem) => {
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
                <span>
                  Context window: <strong>{model.context_window}</strong>
                </span>
                {model.env_key && (
                  <span>
                    Env: <code>{model.env_key}</code>
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

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
        <span className="trigger-icon-slot">
          {isLocalActive ? <Cpu size={13} className="trigger-provider-icon" /> : <Cloud size={13} className="trigger-provider-icon" />}
        </span>
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
            <span className="popover-title">Model Architecture</span>
            <span className="popover-subtitle">
              {models.length} models • Zero-cost local default
            </span>
          </div>

          <div className="model-items-list">
            {/* Local Models Group */}
            {localModels.length > 0 && (
              <div className="model-group-section" data-testid="group-local-models">
                <div className="model-group-header">
                  <span className="group-title">Local Models</span>
                  <span className="group-meta">100% Free &amp; Private</span>
                </div>
                {localModels.map(renderModelRow)}
              </div>
            )}

            {/* Cloud APIs Group */}
            {cloudModels.length > 0 && (
              <div className="model-group-section" data-testid="group-cloud-models">
                <div className="model-group-header">
                  <span className="group-title">Cloud APIs</span>
                  <span className="group-meta">Commercial &amp; Free Tier</span>
                </div>
                {cloudModels.map(renderModelRow)}
              </div>
            )}
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
      <ProviderStatusModal
        isOpen={isStatusModalOpen}
        onClose={() => setIsStatusModalOpen(false)}
      />
    </div>
  );
};
