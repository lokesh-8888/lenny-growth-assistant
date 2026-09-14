import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ArtifactViewer } from '../components/ArtifactViewer';
import type { ArtifactData } from '../components/ArtifactViewer';

describe('ArtifactViewer Component', () => {
  beforeEach(() => {
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  const mockHtmlArtifact: ArtifactData = {
    id: 'test-html-1',
    type: 'html',
    title: 'CAC Payback Simulator',
    word_count: 250,
    content: '<!DOCTYPE html><html><head><title>CAC</title></head><body><h1>Interactive Calculator</h1></body></html>',
  };

  const mockMarkdownArtifact: ArtifactData = {
    id: 'test-md-1',
    type: 'markdown',
    title: 'Executive Brief: Retention Loops',
    word_count: 350,
    content: '# Executive Brief: Retention Loops\n\n## Executive Summary\nCompounding growth relies on retention.\n\n* **Pillar 1**: Habits\n* **Pillar 2**: Expansion',
  };

  it('renders HTML artifact in a sandboxed iframe by default', () => {
    const { container } = render(<ArtifactViewer artifact={mockHtmlArtifact} />);

    // Check title in heading
    expect(screen.getByRole('heading', { level: 3, name: 'CAC Payback Simulator' })).toBeInTheDocument();
    expect(screen.getByText('Interactive HTML')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Rendered/i })).toHaveClass('active');

    // Query iframe directly inside container
    const iframe = container.querySelector('iframe.sandboxed-iframe');
    expect(iframe).toBeInTheDocument();
    expect(iframe?.getAttribute('sandbox')).toBe('allow-scripts');
  });

  it('switches between Rendered and Raw Source view tabs', () => {
    render(<ArtifactViewer artifact={mockHtmlArtifact} />);

    // Click Raw Source tab
    const sourceTab = screen.getByRole('tab', { name: /Raw Source/i });
    fireEvent.click(sourceTab);

    expect(sourceTab).toHaveClass('active');
    expect(screen.getByTestId('source-panel')).toBeInTheDocument();
    expect(screen.getByText(/<!DOCTYPE html>/)).toBeInTheDocument();

    // Click Rendered tab back
    const renderedTab = screen.getByRole('tab', { name: /Rendered/i });
    fireEvent.click(renderedTab);

    expect(renderedTab).toHaveClass('active');
    expect(screen.getByTestId('rendered-panel')).toBeInTheDocument();
  });

  it('renders Markdown artifact with formatted headers and list items', () => {
    render(<ArtifactViewer artifact={mockMarkdownArtifact} />);

    // Check header and title
    expect(screen.getByRole('heading', { level: 3, name: 'Executive Brief: Retention Loops' })).toBeInTheDocument();
    expect(screen.getByText('Executive Brief')).toBeInTheDocument();

    // Check rendered markdown headers
    expect(screen.getByRole('heading', { level: 1, name: /Executive Brief: Retention Loops/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /Executive Summary/i })).toBeInTheDocument();
    expect(screen.getByText(/Compounding growth relies on retention/i)).toBeInTheDocument();
  });

  it('handles copy button click and calls clipboard API', async () => {
    render(<ArtifactViewer artifact={mockMarkdownArtifact} />);

    const copyBtn = screen.getByRole('button', { name: /Copy/i });
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockMarkdownArtifact.content);
  });

  it('handles download button click and initiates file download', () => {
    const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
    const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

    render(<ArtifactViewer artifact={mockMarkdownArtifact} />);

    const downloadBtn = screen.getByRole('button', { name: /Download/i });
    fireEvent.click(downloadBtn);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url');

    createObjectURLSpy.mockRestore();
    revokeObjectURLSpy.mockRestore();
  });
});
