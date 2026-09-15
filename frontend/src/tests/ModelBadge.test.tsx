import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '../components/Chat/MessageBubble';
import { ModelSelector } from '../components/Sidebar/ModelSelector';
import { ConfigContext } from '../context/ConfigContext';
import type { MessageItem } from '../api/sessions';

// Mock ArtifactActionToolbar to isolate MessageBubble badge tests
vi.mock('../components/Chat/ArtifactActionToolbar', () => ({
  ArtifactActionToolbar: () => null,
}));

describe('ModelBadge & Telemetry Transparency Tests', () => {
  const baseMessage: MessageItem = {
    id: 'msg-1',
    session_id: 'sess-1',
    role: 'assistant',
    content: 'According to Lenny Rachitsky, market expansion occurs after retention stabilization.',
    citations: [],
    created_at: '2026-09-15T00:00:00Z',
  };

  it('renders standard local Ollama model badge on assistant message', () => {
    const message: MessageItem = {
      ...baseMessage,
      served_by: 'llama3.1:8b',
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText('llama3.1:8b')).toBeInTheDocument();
    expect(screen.queryByText(/Ollama Fallback/i)).not.toBeInTheDocument();
  });

  it('renders cloud provider model badge when served by cloud', () => {
    const message: MessageItem = {
      ...baseMessage,
      served_by: 'llama-3.3-70b-versatile',
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText('llama-3.3-70b-versatile')).toBeInTheDocument();
    expect(screen.queryByText(/Ollama Fallback/i)).not.toBeInTheDocument();
  });

  it('renders warning fallback badge when served_by is ollama-fallback', () => {
    const message: MessageItem = {
      ...baseMessage,
      served_by: 'ollama-fallback',
    };

    render(<MessageBubble message={message} />);

    // Warning fallback badge must be present
    expect(screen.getByText('Ollama Fallback')).toBeInTheDocument();
    const fallbackTag = screen.getByTitle(/Served via local Ollama after cloud rate limit/i);
    expect(fallbackTag).toBeInTheDocument();
  });

  it('does not render model badge for user messages', () => {
    const userMessage: MessageItem = {
      id: 'msg-2',
      session_id: 'sess-1',
      role: 'user',
      content: 'How do you measure product-market fit?',
      citations: [],
      served_by: 'llama3.1:8b',
      created_at: '2026-09-15T00:00:00Z',
    };

    render(<MessageBubble message={userMessage} />);

    expect(screen.queryByText('llama3.1:8b')).not.toBeInTheDocument();
    expect(screen.queryByText(/Ollama Fallback/i)).not.toBeInTheDocument();
  });

  it('renders active engine and resilience banner in ModelSelector', () => {
    const mockContextValue = {
      config: {
        current_provider: 'ollama-fallback',
        current_model: 'llama3.1:8b',
        available_providers: ['ollama', 'groq'],
        ollama_model: 'llama3.1:8b',
        cloud_provider: 'groq',
        cloud_model: 'llama-3.3-70b-versatile',
        cloud_configured: true,
      },
      health: {
        status: 'healthy' as const,
        dependencies: {
          postgres: { status: 'connected', latency_ms: 1.2 },
          ollama: { status: 'reachable', models_available: 'llama3.1:8b' },
          cloud_llm: { provider: 'groq', configured: true },
        },
      },
      isLoading: false,
      error: null,
      refreshConfig: async () => {},
    };

    render(
      <ConfigContext.Provider value={mockContextValue}>
        <ModelSelector />
      </ConfigContext.Provider>
    );

    expect(screen.getByText('Active LLM Engine')).toBeInTheDocument();
    expect(screen.getByText('Vector Memory')).toBeInTheDocument();
    expect(screen.getByText('Postgres 16')).toBeInTheDocument();
    expect(
      screen.getByText(/Resilience active: Cloud provider rate-limited, auto-routed to local Ollama/i)
    ).toBeInTheDocument();
  });
});
