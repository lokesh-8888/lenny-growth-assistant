import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as artifactsApi from '../api/artifacts';
import * as sessionsApi from '../api/sessions';
import * as configApi from '../api/config';

vi.mock('../api/artifacts');
vi.mock('../api/sessions');
vi.mock('../api/config');
vi.mock('../api/chat');

describe('ArtifactAction and Viewer Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(configApi.getConfig).mockResolvedValue({
      current_provider: 'ollama',
      current_model: 'llama3.1:8b',
      available_providers: ['ollama'],
      cloud_configured: false,
    });

    vi.mocked(configApi.getHealth).mockResolvedValue({
      status: 'healthy',
      dependencies: {
        postgres: { status: 'connected' },
        ollama: { status: 'connected' },
      },
    });

    vi.mocked(sessionsApi.listSessions).mockResolvedValue([
      {
        id: 'session-201',
        title: 'Growth Strategy',
        created_at: '2026-09-15T00:00:00Z',
        updated_at: '2026-09-15T00:00:00Z',
        message_count: 2,
      },
    ]);

    vi.mocked(sessionsApi.getSessionMessages).mockResolvedValue([
      {
        id: 'msg-user-1',
        session_id: 'session-201',
        role: 'user',
        content: 'What are the 4 growth competencies?',
        citations: [],
        created_at: '2026-09-15T00:00:00Z',
      },
      {
        id: 'msg-assist-1',
        session_id: 'session-201',
        role: 'assistant',
        content: 'Adam Fishman identifies 4 competencies: Execution, Customer Knowledge, Strategy, and Influence.',
        citations: [
          {
            guest: 'Adam Fishman',
            episode_title: 'Building High-Performing Teams',
          },
        ],
        served_by: 'llama3.1:8b',
        created_at: '2026-09-15T00:01:00Z',
      },
    ]);

    vi.mocked(artifactsApi.getSessionArtifacts).mockResolvedValue([]);
  });

  it('renders quick action buttons under assistant message', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('artifact-actions-toolbar')).toBeInTheDocument();
    });

    expect(screen.getByTestId('generate-ship30-btn')).toBeInTheDocument();
    expect(screen.getByTestId('generate-markdown-btn')).toBeInTheDocument();
    expect(screen.getByTestId('generate-html-btn')).toBeInTheDocument();
  });

  it('clicking Ship 30 Essay button calls generateArtifact and renders viewer pane', async () => {
    vi.mocked(artifactsApi.generateArtifact).mockResolvedValue({
      id: 'art-ship30-101',
      session_id: 'session-201',
      type: 'ship30',
      title: 'The 4 Growth Competencies Engine',
      content: '# The 4 Growth Competencies Engine\n\nAdam Fishman breaks down execution, customer knowledge, strategy, and influence.',
      word_count: 1250,
      citations: [
        {
          guest: 'Adam Fishman',
          episode_title: 'Building High-Performing Teams',
        },
      ],
      created_at: '2026-09-15T00:02:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('generate-ship30-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('generate-ship30-btn'));

    await waitFor(() => {
      expect(artifactsApi.generateArtifact).toHaveBeenCalledWith(
        expect.objectContaining({
          session_id: 'session-201',
          type: 'ship30',
          title: undefined,
          source_message_id: 'msg-assist-1',
        })
      );
      expect(screen.getByTestId('artifact-viewer')).toBeInTheDocument();
    });

    expect(screen.getAllByText('The 4 Growth Competencies Engine').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/1,250 words/i)).toBeInTheDocument();
  });

  it('allows closing the artifact viewer to return to single pane view', async () => {
    vi.mocked(artifactsApi.generateArtifact).mockResolvedValue({
      id: 'art-html-102',
      session_id: 'session-201',
      type: 'html',
      title: 'CAC Simulator Widget',
      content: '<html><body><div id="app">Calculator</div></body></html>',
      word_count: 300,
      citations: [],
      created_at: '2026-09-15T00:03:00Z',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('generate-html-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('generate-html-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('artifact-viewer')).toBeInTheDocument();
    });

    // Close the viewer using the close button in the artifact toolbar
    const closeBtn = screen.getByTestId('close-artifact-btn');
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('artifact-viewer')).not.toBeInTheDocument();
    });
  });
});
