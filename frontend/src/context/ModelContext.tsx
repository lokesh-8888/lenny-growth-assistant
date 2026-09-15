import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import { getModels } from '../api/models';
import type { ModelItem } from '../api/models';

export const LOCAL_STORAGE_MODEL_KEY = 'lenny_selected_model';
export const DEFAULT_MODEL_ID = 'ollama:llama3.2:3b';

interface ModelContextValue {
  models: ModelItem[];
  selectedModelId: string;
  selectedModel: ModelItem | null;
  isLoading: boolean;
  error: string | null;
  isStatusModalOpen: boolean;
  setIsStatusModalOpen: (open: boolean) => void;
  setSelectedModelId: (modelId: string) => void;
  refreshModels: () => Promise<void>;
}

export const ModelContext = createContext<ModelContextValue | undefined>(undefined);

export const ModelProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [models, setModels] = useState<ModelItem[]>([]);
  const [selectedModelId, setSelectedModelIdState] = useState<string>(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_MODEL_KEY);
      return saved || DEFAULT_MODEL_ID;
    } catch {
      return DEFAULT_MODEL_ID;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState<boolean>(false);

  const fetchModels = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getModels();
      setModels(data);
    } catch (err: any) {
      console.error('Failed to fetch model catalog:', err);
      setError(err?.message || 'Failed to fetch models');
      // Fallback default list if API offline
      setModels([
        {
          id: 'ollama:llama3.2:3b',
          name: 'Llama 3.2 (3B)',
          provider: 'Ollama',
          tier: 'Local',
          badge: 'Fast',
          description: 'Zero-cost local 3B model running via Ollama.',
          context_window: '128k tokens',
          is_local: true,
          is_available: true,
        },
        {
          id: 'ollama:llama3.1:8b',
          name: 'Llama 3.1 (8B)',
          provider: 'Ollama',
          tier: 'Local',
          badge: 'Quality',
          description: 'High quality local 8B model with strong reasoning.',
          context_window: '128k tokens',
          is_local: true,
          is_available: true,
        },
        {
          id: 'google:gemini-1.5-flash',
          name: 'Gemini 1.5 Flash',
          provider: 'Google',
          tier: 'Free Tier',
          badge: 'Fast',
          description: 'Google lightweight high-speed model with generous 15 RPM free tier.',
          context_window: '1M tokens',
          is_local: false,
          env_key: 'GEMINI_API_KEY',
          is_available: false,
        },
        {
          id: 'groq:llama-3.3-70b-versatile',
          name: 'Groq Llama 3.3 (70B)',
          provider: 'Groq',
          tier: 'Free Tier',
          badge: 'Ultra-Fast',
          description: 'Llama 3.3 70B served with ultra-low latency on Groq LPUs.',
          context_window: '128k tokens',
          is_local: false,
          env_key: 'GROQ_API_KEY',
          is_available: false,
        },
        {
          id: 'anthropic:claude-3-5-sonnet',
          name: 'Claude 3.5 Sonnet',
          provider: 'Anthropic',
          tier: 'API Key',
          badge: 'Reasoning',
          description: 'State-of-the-art frontier model with superior reasoning.',
          context_window: '200k tokens',
          is_local: false,
          env_key: 'ANTHROPIC_API_KEY',
          is_available: false,
        },
        {
          id: 'openai:gpt-4o-mini',
          name: 'GPT-4o Mini',
          provider: 'OpenAI',
          tier: 'API Key',
          badge: 'Fast',
          description: 'Fast and cost-effective OpenAI model for agile tasks.',
          context_window: '128k tokens',
          is_local: false,
          env_key: 'OPENAI_API_KEY',
          is_available: false,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const setSelectedModelId = useCallback((id: string) => {
    setSelectedModelIdState(id);
    try {
      localStorage.setItem(LOCAL_STORAGE_MODEL_KEY, id);
    } catch (e) {
      console.warn('Failed to save selected model to localStorage:', e);
    }
  }, []);

  const selectedModel = useMemo(() => {
    return models.find((m) => m.id === selectedModelId) || null;
  }, [models, selectedModelId]);

  return (
    <ModelContext.Provider
      value={{
        models,
        selectedModelId,
        selectedModel,
        isLoading,
        error,
        isStatusModalOpen,
        setIsStatusModalOpen,
        setSelectedModelId,
        refreshModels: fetchModels,
      }}
    >
      {children}
    </ModelContext.Provider>
  );
};

export function useModel(): ModelContextValue {
  const context = useContext(ModelContext);
  if (!context) {
    throw new Error('useModel must be used within a ModelProvider');
  }
  return context;
}
