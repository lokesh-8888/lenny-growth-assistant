import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SessionList } from '../components/Sidebar/SessionList';
import { ChatProvider } from '../context/ChatContext';
import * as sessionsApi from '../api/sessions';
import * as artifactsApi from '../api/artifacts';

// Mock the API layer
vi.mock('../api/sessions');
vi.mock('../api/artifacts');

describe('SessionList Component', () => {
  const mockSessions = [
    {
      id: 'session-1',
      title: 'Growth Competency Consultation',
      created_at: '2026-09-15T00:00:00Z',
      updated_at: '2026-09-15T01:00:00Z',
      message_count: 4,
    },
    {
      id: 'session-2',
      title: 'PLG Loops Exploration',
      created_at: '2026-09-14T00:00:00Z',
      updated_at: '2026-09-14T02:00:00Z',
      message_count: 2,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(sessionsApi.listSessions).mockResolvedValue(mockSessions);
    vi.mocked(sessionsApi.getSessionMessages).mockResolvedValue([]);
    vi.mocked(artifactsApi.getSessionArtifacts).mockResolvedValue([]);
    window.confirm = vi.fn().mockReturnValue(true);
  });

  it('renders session list items correctly', async () => {
    render(
      <ChatProvider>
        <SessionList />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Growth Competency Consultation')).toBeInTheDocument();
      expect(screen.getByText('PLG Loops Exploration')).toBeInTheDocument();
    });

    expect(screen.getByText('4 msgs')).toBeInTheDocument();
    expect(screen.getByText('2 msgs')).toBeInTheDocument();
  });

  it('creates a new session when "+ New Chat" is clicked', async () => {
    const newSession = {
      id: 'session-3',
      title: 'New Growth Consultation',
      created_at: '2026-09-15T02:00:00Z',
      updated_at: '2026-09-15T02:00:00Z',
      message_count: 0,
    };
    vi.mocked(sessionsApi.createSession).mockResolvedValue(newSession);

    render(
      <ChatProvider>
        <SessionList />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Growth Competency Consultation')).toBeInTheDocument();
    });

    const newChatBtn = screen.getByTestId('new-chat-button');
    fireEvent.click(newChatBtn);

    await waitFor(() => {
      expect(sessionsApi.createSession).toHaveBeenCalledWith('New Growth Consultation');
      expect(screen.getByText('New Growth Consultation')).toBeInTheDocument();
    });
  });

  it('selects session when clicked', async () => {
    render(
      <ChatProvider>
        <SessionList />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('PLG Loops Exploration')).toBeInTheDocument();
    });

    const session2Item = screen.getByTestId('session-item-session-2');
    fireEvent.click(session2Item);

    await waitFor(() => {
      expect(sessionsApi.getSessionMessages).toHaveBeenCalledWith('session-2');
    });
  });

  it('deletes session when delete button is confirmed', async () => {
    vi.mocked(sessionsApi.deleteSession).mockResolvedValue(undefined);

    render(
      <ChatProvider>
        <SessionList />
      </ChatProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Growth Competency Consultation')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByTestId('delete-session-session-1');
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(sessionsApi.deleteSession).toHaveBeenCalledWith('session-1');
      expect(screen.queryByText('Growth Competency Consultation')).not.toBeInTheDocument();
    });
  });
});
