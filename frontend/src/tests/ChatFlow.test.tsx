import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatContainer } from '../components/Chat/ChatContainer';
import { ChatProvider } from '../context/ChatContext';
import * as chatApi from '../api/chat';
import * as sessionsApi from '../api/sessions';
import * as artifactsApi from '../api/artifacts';

vi.mock('../api/chat');
vi.mock('../api/sessions');
vi.mock('../api/artifacts');

describe('ChatFlow Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(sessionsApi.listSessions).mockResolvedValue([
      {
        id: 'session-101',
        title: 'PLG Loops',
        created_at: '2026-09-15T00:00:00Z',
        updated_at: '2026-09-15T00:00:00Z',
        message_count: 0,
      },
    ]);
    vi.mocked(sessionsApi.createSession).mockResolvedValue({
      id: 'session-101',
      title: 'PLG Loops',
      created_at: '2026-09-15T00:00:00Z',
      updated_at: '2026-09-15T00:00:00Z',
    });
    vi.mocked(sessionsApi.getSessionMessages).mockResolvedValue([]);
    vi.mocked(artifactsApi.getSessionArtifacts).mockResolvedValue([]);
  });

  it('renders empty state with starter prompts when there are no messages', async () => {
    render(
      <ChatProvider>
        <ChatContainer />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('chat-empty-state')).toBeInTheDocument();
    });

    expect(screen.getByText('What growth challenge are you tackling?')).toBeInTheDocument();
    expect(screen.getByText('Growth Team Competencies')).toBeInTheDocument();
    expect(screen.getByText('Product-Led Growth Loops')).toBeInTheDocument();
  });

  it('clicking a starter prompt sends the message and renders the assistant response', async () => {
    vi.mocked(chatApi.sendChatMessage).mockResolvedValue({
      message_id: 'msg-assist-1',
      session_id: 'session-101',
      role: 'assistant',
      content: 'According to Adam Fishman, high-performing growth teams require 4 competencies.',
      citations: [
        {
          guest: 'Adam Fishman',
          episode_title: 'How to build a high-performing growth team',
          source_url: 'https://www.lennyspodcast.com/transcript',
        },
      ],
      served_by: 'llama3.1:8b',
      is_grounded: true,
    });

    render(
      <ChatProvider>
        <ChatContainer />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('starter-prompt-0')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('starter-prompt-0'));

    await waitFor(() => {
      expect(chatApi.sendChatMessage).toHaveBeenCalled();
      expect(screen.getByText(/According to Adam Fishman/i)).toBeInTheDocument();
    });

    // Check citation section
    expect(screen.getByTestId('citation-container')).toBeInTheDocument();
    expect(screen.getByText(/1 Grounded Source Cited/i)).toBeInTheDocument();

    // Toggle citations
    fireEvent.click(screen.getByText(/1 Grounded Source Cited/i));
    expect(screen.getByText('Adam Fishman')).toBeInTheDocument();
    expect(screen.getByText('How to build a high-performing growth team')).toBeInTheDocument();
  });

  it('submits text via textarea and Enter key', async () => {
    vi.mocked(chatApi.sendChatMessage).mockResolvedValue({
      message_id: 'msg-assist-2',
      session_id: 'session-101',
      role: 'assistant',
      content: 'Elena Verna emphasizes compounding retention loops.',
      citations: [],
      served_by: 'ollama-fallback',
      is_grounded: true,
    });

    render(
      <ChatProvider>
        <ChatContainer />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('chat-input-textarea')).toBeInTheDocument();
    });

    const textarea = screen.getByTestId('chat-input-textarea');
    fireEvent.change(textarea, { target: { value: 'How does Elena Verna define loops?' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', charCode: 13 });

    await waitFor(() => {
      expect(chatApi.sendChatMessage).toHaveBeenCalledWith({
        session_id: 'session-101',
        message: 'How does Elena Verna define loops?',
      });
      expect(screen.getByText(/Elena Verna emphasizes/i)).toBeInTheDocument();
    });

    // Verify fallback badge rendered
    expect(screen.getByText('Ollama Fallback')).toBeInTheDocument();
  });
});
