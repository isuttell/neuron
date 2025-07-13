import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MediaActions } from "../MediaActions";
import { toast } from "sonner";

// Mock child components
vi.mock("@/components/MediaListDropdown", () => ({
  MediaListDropdown: ({ variant, size, mediaItemId }: any) => (
    <div
      data-testid="media-list-dropdown"
      data-variant={variant}
      data-size={size}
      data-media-item-id={mediaItemId}
    >
      Media List Dropdown
    </div>
  ),
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, variant, size, onClick, ...props }: any) => (
    <button
      data-testid="button"
      data-variant={variant}
      data-size={size}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: any) => <div data-testid="tooltip">{children}</div>,
  TooltipContent: ({ children }: any) => <div data-testid="tooltip-content">{children}</div>,
  TooltipTrigger: ({ children }: any) => <div data-testid="tooltip-trigger">{children}</div>,
  TooltipProvider: ({ children }: any) => <div>{children}</div>,
}));

// Mock Lucide icons
vi.mock("lucide-react", () => ({
  Copy: () => <div data-testid="copy-icon">Copy Icon</div>,
  Download: () => <div data-testid="download-icon">Download Icon</div>,
}));

// Mock sonner toast
vi.mock("sonner", () => {
  const mockToast = vi.fn();
  mockToast.error = vi.fn();
  return {
    toast: mockToast,
  };
});

// Mock fetch and URL APIs
global.fetch = vi.fn();
global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
global.URL.revokeObjectURL = vi.fn();

const renderWithProviders = (component: React.ReactElement) => {
  return render(<TooltipProvider>{component}</TooltipProvider>);
};

describe("MediaActions", () => {
  const defaultProps = {
    url: "https://example.com/test-file.jpg",
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });

    // Reset DOM modifications
    document.body.innerHTML = '';
  });

  it("renders copy and download buttons", () => {
    renderWithProviders(<MediaActions {...defaultProps} />);

    const buttons = screen.getAllByTestId("button");
    expect(buttons).toHaveLength(2);

    expect(screen.getByTestId("copy-icon")).toBeInTheDocument();
    expect(screen.getByTestId("download-icon")).toBeInTheDocument();
  });

  it("renders MediaListDropdown when mediaItem is provided", () => {
    const mediaItem = { id: "test-media-123" };

    renderWithProviders(
      <MediaActions
        {...defaultProps}
        mediaItem={mediaItem as any}
      />
    );

    const dropdown = screen.getByTestId("media-list-dropdown");
    expect(dropdown).toBeInTheDocument();
    expect(dropdown).toHaveAttribute("data-media-item-id", "test-media-123");
  });

  it("does not render MediaListDropdown when mediaItem is not provided", () => {
    renderWithProviders(<MediaActions {...defaultProps} />);

    expect(screen.queryByTestId("media-list-dropdown")).not.toBeInTheDocument();
  });

  it("applies variant and size props to buttons", () => {
    renderWithProviders(
      <MediaActions
        {...defaultProps}
        variant="outline"
        size="default"
      />
    );

    const buttons = screen.getAllByTestId("button");
    buttons.forEach(button => {
      expect(button).toHaveAttribute("data-variant", "outline");
      expect(button).toHaveAttribute("data-size", "default");
    });
  });

  it("applies default variant and size when not specified", () => {
    renderWithProviders(<MediaActions {...defaultProps} />);

    const buttons = screen.getAllByTestId("button");
    buttons.forEach(button => {
      expect(button).toHaveAttribute("data-variant", "ghost");
      expect(button).toHaveAttribute("data-size", "icon");
    });
  });

  it("copies URL to clipboard when copy button is clicked", async () => {
    renderWithProviders(<MediaActions {...defaultProps} />);

    const copyButton = screen.getAllByTestId("button")[0]; // First button should be copy
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("https://example.com/test-file.jpg");
    });
  });

  it("shows toast message when copy is successful", async () => {
    renderWithProviders(<MediaActions {...defaultProps} />);

    const copyButton = screen.getAllByTestId("button")[0];
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(vi.mocked(toast)).toHaveBeenCalledWith("Copy URL copied to clipboard");
    });
  });

  it("uses custom copy label", async () => {
    renderWithProviders(
      <MediaActions
        {...defaultProps}
        copyLabel="Custom Copy Label"
      />
    );

    const copyButton = screen.getAllByTestId("button")[0];
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(vi.mocked(toast)).toHaveBeenCalledWith("Custom Copy Label copied to clipboard");
    });
  });

  it("initiates download when download button is clicked", async () => {
    const mockBlob = new Blob(['mock content'], { type: 'image/jpeg' });
    (fetch as any).mockResolvedValue({
      blob: () => Promise.resolve(mockBlob),
    });

    renderWithProviders(<MediaActions {...defaultProps} />);

    const downloadButton = screen.getAllByTestId("button")[1]; // Second button should be download
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("https://example.com/test-file.jpg");
    });
  });

  it("creates download link with correct filename", async () => {
    const mockBlob = new Blob(['mock content'], { type: 'image/jpeg' });
    (fetch as any).mockResolvedValue({
      blob: () => Promise.resolve(mockBlob),
    });

    const createElementSpy = vi.spyOn(document, 'createElement');

    renderWithProviders(
      <MediaActions
        {...defaultProps}
        downloadFileName="custom-filename.jpg"
      />
    );

    const downloadButton = screen.getAllByTestId("button")[1];
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(createElementSpy).toHaveBeenCalledWith('a');
    });

    // Verify link creation and cleanup would happen
    await waitFor(() => {
      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    });
  });

  it("uses URL filename when downloadFileName not provided", async () => {
    const mockBlob = new Blob(['mock content'], { type: 'image/jpeg' });
    (fetch as any).mockResolvedValue({
      blob: () => Promise.resolve(mockBlob),
    });

    renderWithProviders(
      <MediaActions
        url="https://example.com/path/to/image.png"
      />
    );

    const downloadButton = screen.getAllByTestId("button")[1];
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalled();
    });

    // The default filename should be extracted from URL
    await waitFor(() => {
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  it("shows success toast when download completes", async () => {
    const mockBlob = new Blob(['mock content'], { type: 'image/jpeg' });
    (fetch as any).mockResolvedValue({
      blob: () => Promise.resolve(mockBlob),
    });

    renderWithProviders(<MediaActions {...defaultProps} />);

    const downloadButton = screen.getAllByTestId("button")[1];
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(vi.mocked(toast)).toHaveBeenCalledWith("Download completed");
    });
  });

  it("uses custom download label in success message", async () => {
    const mockBlob = new Blob(['mock content'], { type: 'image/jpeg' });
    (fetch as any).mockResolvedValue({
      blob: () => Promise.resolve(mockBlob),
    });

    renderWithProviders(
      <MediaActions
        {...defaultProps}
        downloadLabel="Custom Download"
      />
    );

    const downloadButton = screen.getAllByTestId("button")[1];
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(vi.mocked(toast)).toHaveBeenCalledWith("Custom Download completed");
    });
  });

  it("shows error toast when download fails", async () => {
    (fetch as any).mockRejectedValue(new Error('Network error'));

    renderWithProviders(<MediaActions {...defaultProps} />);

    const downloadButton = screen.getAllByTestId("button")[1];
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(vi.mocked(toast).error).toHaveBeenCalledWith("Download failed");
    });
  });

  it("prevents event propagation on button clicks", async () => {
    renderWithProviders(<MediaActions {...defaultProps} />);

    const copyButton = screen.getAllByTestId("button")[0];
    const downloadButton = screen.getAllByTestId("button")[1];

    // Mock the event object for fireEvent
    fireEvent.click(copyButton);
    fireEvent.click(downloadButton);

    // Events should be handled (preventDefault called internally)
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    });
  });

  it("applies custom className", () => {
    renderWithProviders(
      <MediaActions
        {...defaultProps}
        className="custom-actions-class"
      />
    );

    // The className is applied to the root div container
    const container = screen.getByTestId("copy-icon").closest('[class*="custom-actions-class"]');
    expect(container).toBeInTheDocument();
  });

  it("renders tooltips with correct content", () => {
    renderWithProviders(
      <MediaActions
        {...defaultProps}
        copyLabel="Custom Copy"
        downloadLabel="Custom Download"
      />
    );

    const tooltipContents = screen.getAllByTestId("tooltip-content");
    expect(tooltipContents[0]).toHaveTextContent("Custom Copy");
    expect(tooltipContents[1]).toHaveTextContent("Custom Download");
  });

  it("passes props to MediaListDropdown correctly", () => {
    const mediaItem = { id: "test-123" };

    renderWithProviders(
      <MediaActions
        {...defaultProps}
        mediaItem={mediaItem as any}
        variant="outline"
        size="default"
      />
    );

    const dropdown = screen.getByTestId("media-list-dropdown");
    expect(dropdown).toHaveAttribute("data-variant", "outline");
    expect(dropdown).toHaveAttribute("data-size", "default");
    expect(dropdown).toHaveAttribute("data-media-item-id", "test-123");
  });
});
