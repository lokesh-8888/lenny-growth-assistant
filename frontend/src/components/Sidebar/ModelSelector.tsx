import React from 'react';
import { useConfig } from '../../context/ConfigContext';
import { Database, Server, ShieldAlert } from 'lucide-react';

export const ModelSelector: React.FC = () => {
  const { config, health } = useConfig();

  const isFallback = config?.current_provider === 'ollama-fallback';

  return (
    <div className="sidebar-model-telemetry">
      <div className="telemetry-row">
        <div className="telemetry-label">
          <Server size={13} />
          <span>Active LLM Engine</span>
        </div>
        <span className="telemetry-val">
          {config?.current_provider === 'ollama' ? 'Local Ollama' : config?.current_provider || 'Ollama'}
        </span>
      </div>

      <div className="telemetry-row">
        <div className="telemetry-label">
          <Database size={13} />
          <span>Vector Memory</span>
        </div>
        <span className="telemetry-val">
          {health?.dependencies?.postgres?.status === 'connected' ? 'Postgres 16' : 'Offline'}
        </span>
      </div>

      {isFallback && (
        <div className="telemetry-fallback-note">
          <ShieldAlert size={14} />
          <span>Resilience active: Cloud provider rate-limited, auto-routed to local Ollama.</span>
        </div>
      )}
    </div>
  );
};
