import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModelSelector } from '../components/ModelSelector/ModelSelector';
import { ModelProvider, LOCAL_STORAGE_MODEL_KEY } from '../context/ModelContext';
import { ConfigContext } from '../context/ConfigContext';
import { MessageBubble } from '../components/Chat/MessageBubble';
import type { MessageItem } from '../api/sessions';
import * as modelsApi from '../api/models';

vi.mock('../api/models', () => ({
  getModels: vi.fn(),
}));

vi.mock('../components/Chat/ArtifactActionToolbar', () => ({
  ArtifactActionToolbar: () => null,
}));

describe('ModelSelector Popover & State Persistence Tests', () => {
  const mockCatalog = [
    {
      id: 'ollama:llama3.2:3b',
      name: 'Llama 3.2 (3B)',
      provider: 'Ollama',
      tier: 'Local',
      badge: 'Fast',
      description: 'Zero-cost local 3B model running via Ollama.',
      context_window: '128k tokens',
      is_local: true,
      env_key: null,
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
      env_key: null,
      is_available: true,
    },
    {
      id: 'google:gemini-1.5-flash',
      name: 'Gemini 1.5 Flash',
      provider: 'Google',
      tier: 'Free Tier',
      badge: 'Fast',
      description: 'Google lightweight high-speed model.',
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
      description: 'Llama 3.3 70B served on Groq LPUs.',
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
      description: 'State-of-the-art frontier model.',
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
      description: 'Fast and cost-effective OpenAI model.',
      context_window: '128k tokens',
      is_local: false,
      env_key: 'OPENAI_API_KEY',
      is_available: false,
    },
  ];

  const mockConfigContext = {
    config: {
      current_provider: 'ollama',
      current_model: 'llama3.2:3b',
      available_providers: ['ollama', 'groq', 'gemini'],
      cloud_configured: false,
    },
    health: {
      status: 'healthy',
      dependencies: {
        postgres: { status: 'connected', latency_ms: 1.5 },
        ollama: { status: 'running', models_available: ['llama3.2:3b', 'llama3.1:8b'] },
        cloud_llm: { provider: 'groq', configured: false },
      },
    },
    isLoading: false,
    error: null,
    refreshConfig: async () => {},
  };

  beforeEach(() => {
    localStorage.clear();
    vi.mocked(modelsApi.getModels).mockResolvedValue(mockCatalog);
  });

  it('renders trigger button with active model name and provider', async () => {
    render(
      <ConfigContext.Provider value={mockConfigContext}>
        <ModelProvider>
          <ModelSelector />
        </ModelProvider>
      </ConfigContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('model-selector-trigger')).toBeInTheDocument();
    });

    expect(screen.getByText('Llama 3.2 (3B)')).toBeInTheDocument();
    expect(screen.getByText('Ollama')).toBeInTheDocument();
  });

  it('clicking trigger opens popover with model options and badges', async () => {
    render(
      <ConfigContext.Provider value={mockConfigContext}>
        <ModelProvider>
          <ModelSelector />
        </ModelProvider>
      </ConfigContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('model-selector-trigger')).toBeInTheDocument();
    });

    // Popover is initially closed
    expect(screen.queryByTestId('model-popover-menu')).not.toBeInTheDocument();

    // Click trigger to open
    fireEvent.click(screen.getByTestId('model-selector-trigger'));

    expect(screen.getByTestId('model-popover-menu')).toBeInTheDocument();
    expect(screen.getByText('Gemini 1.5 Flash')).toBeInTheDocument();
    expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument();
    expect(screen.getByText('Groq Llama 3.3 (70B)')).toBeInTheDocument();
    expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument();

    // Badges must be rendered
    expect(screen.getAllByText('Fast').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Reasoning')).toBeInTheDocument();
    expect(screen.getByText('Ultra-Fast')).toBeInTheDocument();
  });

  it('selecting a model updates state and persists choice in localStorage', async () => {
    render(
      <ConfigContext.Provider value={mockConfigContext}>
        <ModelProvider>
          <ModelSelector />
        </ModelProvider>
      </ConfigContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('model-selector-trigger')).toBeInTheDocument();
    });

    // Open popover
    fireEvent.click(screen.getByTestId('model-selector-trigger'));

    // Select Claude 3.5 Sonnet
    const claudeOption = screen.getByTestId('model-option-anthropic:claude-3-5-sonnet');
    fireEvent.click(claudeOption);

    // Popover should close
    expect(screen.queryByTestId('model-popover-menu')).not.toBeInTheDocument();

    // Trigger should reflect new selection
    expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();

    // Choice must be persisted in localStorage
    expect(localStorage.getItem(LOCAL_STORAGE_MODEL_KEY)).toBe('anthropic:claude-3-5-sonnet');
  });

  it('pressing Escape key closes the popover menu', async () => {
    render(
      <ConfigContext.Provider value={mockConfigContext}>
        <ModelProvider>
          <ModelSelector />
        </ModelProvider>
      </ConfigContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('model-selector-trigger')).toBeInTheDocument();
    });

    // Open popover
    fireEvent.click(screen.getByTestId('model-selector-trigger'));
    expect(screen.getByTestId('model-popover-menu')).toBeInTheDocument();

    // Press Escape
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });

    expect(screen.queryByTestId('model-popover-menu')).not.toBeInTheDocument();
  });

  it('clicking View Provider Status opens the telemetry modal', async () => {
    render(
      <ConfigContext.Provider value={mockConfigContext}>
        <ModelProvider>
          <ModelSelector />
        </ModelProvider>
      </ConfigContext.Provider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('model-selector-trigger')).toBeInTheDocument();
    });

    // Open popover
    fireEvent.click(screen.getByTestId('model-selector-trigger'));

    // Click footer action
    const statusBtn = screen.getByTestId('view-provider-status-btn');
    fireEvent.click(statusBtn);

    // Modal must open
    expect(screen.getByTestId('provider-status-modal')).toBeInTheDocument();
    expect(screen.getByText('Zero-Downtime Resilience Guarantee')).toBeInTheDocument();
    expect(screen.getByText('Local Infrastructure')).toBeInTheDocument();
    expect(screen.getByText('Cloud Provider Credentials')).toBeInTheDocument();

    // Close modal
    fireEvent.click(screen.getByLabelText('Close provider modal'));
    expect(screen.queryByTestId('provider-status-modal')).not.toBeInTheDocument();
  });

  it('renders amber fallback badge on assistant message when served_by includes fallback tag', () => {
    const fallbackMessage: MessageItem = {
      id: 'msg-fallback-1',
      session_id: 'sess-1',
      role: 'assistant',
      content: 'Answer generated by Ollama because Claude was unconfigured.',
      citations: [],
      served_by: 'ollama-fallback (requested: anthropic:claude-3-5-sonnet)',
      created_at: '2026-09-15T00:00:00Z',
    };

    render(<MessageBubble message={fallbackMessage} />);

    // Must render amber badge with requested model name and Ollama fallback notice
    expect(screen.getByTestId('message-fallback-badge')).toBeInTheDocument();
    expect(screen.getByText(/Requested Claude 3.5 \(Key Missing\) — Served via Local Ollama Fallback/i)).toBeInTheDocument();
  });
});
