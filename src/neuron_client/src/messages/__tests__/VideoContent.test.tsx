import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TooltipProvider } from "@/components/ui/tooltip";
import VideoContent from "../VideoContent";

// Mock child components
vi.mock("@/components/MediaDialog", () => ({
  default: ({ trigger, title, actions, children, metadata, description }: any) => (
    <div data-testid="media-dialog">
      <div data-testid="dialog-trigger">{trigger}</div>
      <div data-testid="dialog-title">{title}</div>
      <div data-testid="dialog-actions">{actions}</div>
      <div data-testid="dialog-content">{children}</div>
      {description && <div data-testid="dialog-description">{description}</div>}
      {metadata && <div data-testid="dialog-metadata">{JSON.stringify(metadata)}</div>}
    </div>
  ),
}));

vi.mock("@/components/media/VideoRenderer", () => ({
  VideoRenderer: React.forwardRef(({ url, isThumbnail, ...props }: any, ref: any) => (
    <video
      ref={ref}
      data-testid={isThumbnail ? "video-thumbnail" : "video-display"}
      src={url}
      data-props={JSON.stringify({ ...props, isThumbnail })}
    />
  )),
}));

vi.mock("@/components/media/MediaActions", () => ({
  MediaActions: ({ url, variant, size, copyLabel, downloadLabel, downloadFileName }: any) => (
    <div
      data-testid="media-actions"
      data-url={url}
      data-variant={variant}
      data-size={size}
      data-copy-label={copyLabel}
      data-download-label={downloadLabel}
      data-download-filename={downloadFileName}
    />
  ),
}));

// Mock useMediaPlayer hook
const mockRegisterPlayer = vi.fn();
const mockUnregisterPlayer = vi.fn();
const mockPlayPlayer = vi.fn();

vi.mock("@/hooks/useMediaPlayer", () => ({
  useMediaPlayer: () => ({
    registerPlayer: mockRegisterPlayer,
    unregisterPlayer: mockUnregisterPlayer,
    playPlayer: mockPlayPlayer,
  }),
}));

const renderWithProviders = (component: React.ReactElement) => {
  return render(<TooltipProvider>{component}</TooltipProvider>);
};

describe("VideoContent", () => {
  const defaultProps = {
    url: "https://example.com/video.mp4",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with basic props", () => {
    renderWithProviders(<VideoContent {...defaultProps} />);

    expect(screen.getByTestId("media-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("video-thumbnail")).toBeInTheDocument();
    expect(screen.getByTestId("video-display")).toBeInTheDocument();
  });

  it("passes correct props to VideoRenderer thumbnail", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        autoPlay={true}
        controls={true}
        loop={true}
        preload="auto"
        duration={125}
      />
    );

    const thumbnail = screen.getByTestId("video-thumbnail");
    const props = JSON.parse(thumbnail.getAttribute("data-props") || "{}");

    expect(props.autoPlay).toBe(true);
    expect(props.controls).toBe(true);
    expect(props.loop).toBe(true);
    expect(props.muted).toBe(true); // Thumbnails are always muted
    expect(props.preload).toBe("auto");
    expect(props.duration).toBe(125);
    expect(props.isThumbnail).toBe(true);
  });

  it("passes correct props to VideoRenderer display", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
      />
    );

    const display = screen.getByTestId("video-display");
    const props = JSON.parse(display.getAttribute("data-props") || "{}");

    expect(props.autoPlay).toBe(true); // Display always autoplays
    expect(props.controls).toBe(true); // Display always has controls
    expect(props.loop).toBe(true); // Display always loops
    expect(props.muted).toBe(false); // Display is not muted
    expect(props.preload).toBe("auto"); // Display always preloads
    expect(props.isThumbnail).toBe(false);
  });

  it("shows controls when showControls is true", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        showControls={true}
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    expect(mediaActions).toHaveLength(2); // One for thumbnail controls, one for dialog actions
  });

  it("does not show thumbnail controls when showControls is false", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        showControls={false}
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    expect(mediaActions).toHaveLength(1); // Only dialog actions
  });

  it("passes correct MediaActions props for thumbnail controls", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        showControls={true}
        url="https://example.com/test-video.mp4"
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    const thumbnailActions = mediaActions[0];

    expect(thumbnailActions.getAttribute("data-variant")).toBe("outline");
    expect(thumbnailActions.getAttribute("data-copy-label")).toBe("Video URL");
    expect(thumbnailActions.getAttribute("data-download-filename")).toBe("test-video.mp4");
  });

  it("passes correct MediaActions props for dialog actions", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        url="https://example.com/another-video.mp4"
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    const dialogActions = mediaActions[mediaActions.length - 1];

    expect(dialogActions.getAttribute("data-variant")).toBe("ghost");
    expect(dialogActions.getAttribute("data-size")).toBe("default");
    expect(dialogActions.getAttribute("data-copy-label")).toBe("Video URL");
    expect(dialogActions.getAttribute("data-download-label")).toBe("Download video");
    expect(dialogActions.getAttribute("data-download-filename")).toBe("another-video.mp4");
  });

  it("passes metadata to MediaDialog", () => {
    const metadata = {
      model: "test-model",
      duration: 120,
      fps: 30,
      format: "mp4",
      seed: 12345,
    };

    renderWithProviders(
      <VideoContent
        {...defaultProps}
        metadata={metadata}
      />
    );

    expect(screen.getByTestId("dialog-metadata")).toHaveTextContent(JSON.stringify(metadata));
  });

  it("passes description to MediaDialog", () => {
    const description = "A test video showing something interesting";

    renderWithProviders(
      <VideoContent
        {...defaultProps}
        description={description}
      />
    );

    expect(screen.getByTestId("dialog-description")).toHaveTextContent(description);
  });

  it("uses caption as dialog title", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        caption="Custom Video Title"
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Custom Video Title");
  });

  it("uses mediaItem.name as title when caption not provided", () => {
    const mediaItem = { id: "123", name: "Media Item Title" };

    renderWithProviders(
      <VideoContent
        {...defaultProps}
        mediaItem={mediaItem as any}
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Media Item Title");
  });

  it("uses default title when caption and mediaItem.name not provided", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Video Details");
  });

  it("uses mediaItem.description when description not provided", () => {
    const mediaItem = { id: "123", description: "Media item description" };

    renderWithProviders(
      <VideoContent
        {...defaultProps}
        mediaItem={mediaItem as any}
      />
    );

    expect(screen.getByTestId("dialog-description")).toHaveTextContent("Media item description");
  });

  it("applies custom className to trigger container", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        className="custom-video-class"
      />
    );

    const trigger = screen.getByTestId("dialog-trigger");
    expect(trigger.firstChild).toHaveClass("custom-video-class");
  });

  it("uses default className when not provided", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
      />
    );

    const trigger = screen.getByTestId("dialog-trigger");
    expect(trigger.firstChild).toHaveClass("relative", "max-h-[400px]", "max-w-[500px]", "w-fit");
  });

  it("handles mediaItem prop correctly", () => {
    const mediaItem = { id: "test-media-456" };

    renderWithProviders(
      <VideoContent
        {...defaultProps}
        mediaItem={mediaItem as any}
        showControls={true}
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    expect(mediaActions).toHaveLength(2);
  });

  it("uses default prop values", () => {
    renderWithProviders(<VideoContent {...defaultProps} />);

    const thumbnail = screen.getByTestId("video-thumbnail");
    const props = JSON.parse(thumbnail.getAttribute("data-props") || "{}");

    expect(props.autoPlay).toBe(false);
    expect(props.controls).toBe(false);
    expect(props.loop).toBe(false);
    expect(props.preload).toBe("metadata");
  });

  it("handles URLs without filename correctly", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
        url="https://example.com/"
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    const dialogActions = mediaActions[mediaActions.length - 1];

    expect(dialogActions.getAttribute("data-download-filename")).toBe("video.mp4");
  });

  it("registers and unregisters media player correctly", () => {
    const { unmount } = renderWithProviders(
      <VideoContent
        {...defaultProps}
      />
    );

    // Check that registerPlayer was called
    expect(mockRegisterPlayer).toHaveBeenCalled();
    const [id, url, element] = mockRegisterPlayer.mock.calls[0];
    expect(url).toBe("https://example.com/video.mp4");
    expect(element).toBeInstanceOf(HTMLVideoElement);

    // Unmount and check that unregisterPlayer was called
    unmount();
    expect(mockUnregisterPlayer).toHaveBeenCalledWith(id, url);
  });

  it("handles play event correctly", () => {
    renderWithProviders(
      <VideoContent
        {...defaultProps}
      />
    );

    // Check that registerPlayer was called
    expect(mockRegisterPlayer).toHaveBeenCalled();

    // Get the video element from the mock call
    const videoElement = mockRegisterPlayer.mock.calls[0]?.[2];
    expect(videoElement).toBeDefined();

    // Simulate play event
    videoElement.dispatchEvent(new Event("play"));

    // Check that playPlayer was called
    expect(mockPlayPlayer).toHaveBeenCalled();
  });
});
