import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitationCard } from '../components/Chat/CitationCard';
import { QuickActions } from '../components/Chat/QuickActions';
import { ModelDropdown } from '../components/ModelSelector/ModelDropdown';
import { ArtifactControls } from '../components/ArtifactViewer/ArtifactControls';
import { ModelContext } from '../context/ModelContext';
import { ChatContext } from '../context/ChatContext';
import { ConfigContext } from '../context/ConfigContext';
import type { ModelItem } from '../api/models';

describe('Phase 3 Specifications Test Suite', () => {
  describe('1. Expandable Timestamped Citations (CitationCard)', () => {
    const mockCitations = [
      {
        guest: 'Elena Verna',
        episode_title: 'Elena Verna on B2B Growth',
        source_url: 'https://youtube.com/watch?v=mock',
        timestamp: '14:32',
        speaker: 'Elena Verna',
        quote: 'Product-led growth and product-led sales are compounding growth loops.',
        quote_snippet: 'Product-led growth and product-led sales are compounding growth loops.',
      },
    ];

    it('renders citation toggle button and expands on click', () => {
      render(<CitationCard citations={mockCitations} />);

      const toggleBtn = screen.getByTitle('Toggle grounded transcript citations');
      expect(toggleBtn).toBeInTheDocument();
      expect(screen.getByText(/1 grounded source cited/i)).toBeInTheDocument();

      // Expand citations
      fireEvent.click(toggleBtn);

      // Verify podcast icon, guest name, episode title, and timestamp badge
      expect(screen.getByText('Elena Verna')).toBeInTheDocument();
      expect(screen.getByText('Elena Verna on B2B Growth')).toBeInTheDocument();
      expect(screen.getByText('[14:32]')).toBeInTheDocument();

      // Verify quote snippet
      expect(
        screen.getByText(
          '"Product-led growth and product-led sales are compounding growth loops."'
        )
      ).toBeInTheDocument();

      // Verify link to transcript/video
      const link = screen.getByTitle('View original episode transcript or video');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://youtube.com/watch?v=mock');
    });
  });

  describe('2. QuickActions Component', () => {
    it('renders synthesis buttons with proper labels and triggers generation', () => {
      const mockGenerate = vi.fn();
      const mockChatCtx: any = {
        generateArtifactAction: mockGenerate,
        isArtifactGenerating: false,
        generatingType: null,
      };

      render(
        <ChatContext.Provider value={mockChatCtx}>
          <QuickActions messageId="msg-1" />
        </ChatContext.Provider>
      );

      const ship30Btn = screen.getByTestId('generate-ship30-btn');
      expect(ship30Btn).toBeInTheDocument();
      expect(screen.getByText('Turn into Ship 30 Essay')).toBeInTheDocument();

      const briefBtn = screen.getByTestId('generate-markdown-btn');
      expect(briefBtn).toBeInTheDocument();
      expect(screen.getByText('Generate Brief')).toBeInTheDocument();

      const widgetBtn = screen.getByTestId('generate-html-btn');
      expect(widgetBtn).toBeInTheDocument();
      expect(screen.getByText('Interactive Widget')).toBeInTheDocument();

      // Click Ship 30
      fireEvent.click(ship30Btn);
      expect(mockGenerate).toHaveBeenCalledWith('ship30', undefined, 'msg-1');
    });
  });

  describe('3. ModelDropdown Popover & Grouping', () => {
    const mockModels: ModelItem[] = [
      {
        id: 'ollama:llama3.2:3b',
        name: 'Llama 3.2 (3B)',
        provider: 'Ollama',
        tier: 'Local',
        badge: 'Fast',
        description: 'Zero-cost local 3B model.',
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
        description: 'Google high-speed model.',
        context_window: '1M tokens',
        is_local: false,
        env_key: 'GEMINI_API_KEY',
        is_available: false,
      },
      {
        id: 'anthropic:claude-3-5-sonnet',
        name: 'Claude 3.5 Sonnet',
        provider: 'Anthropic',
        tier: 'API Key',
        badge: 'Reasoning',
        description: 'Frontier reasoning model.',
        context_window: '200k tokens',
        is_local: false,
        env_key: 'ANTHROPIC_API_KEY',
        is_available: false,
      },
    ];

    it('renders active model trigger and opens grouped popover list', async () => {
      const mockSetModel = vi.fn();
      const mockModelCtx: any = {
        models: mockModels,
        selectedModelId: 'ollama:llama3.2:3b',
        selectedModel: mockModels[0],
        setSelectedModelId: mockSetModel,
        isStatusModalOpen: false,
        setIsStatusModalOpen: vi.fn(),
      };
      const mockConfigCtx: any = {
        health: { status: 'healthy', dependencies: {} },
      };

      render(
        <ConfigContext.Provider value={mockConfigCtx}>
          <ModelContext.Provider value={mockModelCtx}>
            <ModelDropdown />
          </ModelContext.Provider>
        </ConfigContext.Provider>
      );

      // Trigger button
      const trigger = screen.getByTestId('model-selector-trigger');
      expect(trigger).toHaveTextContent('Llama 3.2 (3B)');
      expect(trigger).toHaveTextContent('Ollama');

      // Open popover
      fireEvent.click(trigger);

      expect(screen.getByTestId('model-popover-menu')).toBeInTheDocument();
      expect(screen.getByTestId('group-local-models')).toBeInTheDocument();
      expect(screen.getByTestId('group-cloud-models')).toBeInTheDocument();

      // Check active checkmark on selected model
      expect(screen.getByTestId('selected-check-icon')).toBeInTheDocument();

      // Capability badges
      expect(screen.getAllByText('Fast').length).toBeGreaterThan(0);
      expect(screen.getByText('Reasoning')).toBeInTheDocument();

      // Key missing badge on unconfigured cloud model
      expect(screen.getAllByText('Key missing').length).toBeGreaterThan(0);

      // Click to select Claude 3.5 Sonnet
      const claudeOption = screen.getByTestId('model-option-anthropic:claude-3-5-sonnet');
      fireEvent.click(claudeOption);
      expect(mockSetModel).toHaveBeenCalledWith('anthropic:claude-3-5-sonnet');
    });
  });

  describe('4. ArtifactControls Component', () => {
    it('handles tab switching, copy, download, and close', () => {
      const onTabChange = vi.fn();
      const onCopy = vi.fn();
      const onDownload = vi.fn();
      const onToggleFullscreen = vi.fn();
      const onClose = vi.fn();

      render(
        <ArtifactControls
          title="Growth Strategy Essay"
          type="ship30"
          wordCount={1250}
          activeTab="rendered"
          onTabChange={onTabChange}
          onCopy={onCopy}
          onDownload={onDownload}
          isFullscreen={false}
          onToggleFullscreen={onToggleFullscreen}
          onClose={onClose}
        />
      );

      expect(screen.getByText('Growth Strategy Essay')).toBeInTheDocument();
      expect(screen.getByText('1,250 words')).toBeInTheDocument();

      // Tabs
      const rawTab = screen.getByText('Raw Source');
      fireEvent.click(rawTab);
      expect(onTabChange).toHaveBeenCalledWith('source');

      // Copy
      const copyBtn = screen.getByTitle('Copy raw artifact source');
      fireEvent.click(copyBtn);
      expect(onCopy).toHaveBeenCalled();

      // Download
      const downloadBtn = screen.getByTitle('Download .md');
      fireEvent.click(downloadBtn);
      expect(onDownload).toHaveBeenCalled();

      // Close
      const closeBtn = screen.getByTestId('close-artifact-btn');
      fireEvent.click(closeBtn);
      expect(onClose).toHaveBeenCalled();
    });
  });
});
