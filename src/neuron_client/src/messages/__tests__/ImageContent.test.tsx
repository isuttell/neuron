import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TooltipProvider } from "@/components/ui/tooltip";
import ImageContent from "../ImageContent";

// Mock child components
vi.mock("@/components/MediaDialog", () => ({
  default: ({ trigger, title, actions, children, metadata, description, dimensions }: any) => (
    <div data-testid="media-dialog">
      <div data-testid="dialog-trigger">{trigger}</div>
      <div data-testid="dialog-title">{title}</div>
      <div data-testid="dialog-actions">{actions}</div>
      <div data-testid="dialog-content">{children}</div>
      {description && <div data-testid="dialog-description">{description}</div>}
      {metadata && <div data-testid="dialog-metadata">{JSON.stringify(metadata)}</div>}
      {dimensions && <div data-testid="dialog-dimensions">{JSON.stringify(dimensions)}</div>}
    </div>
  ),
}));

vi.mock("@/components/media/ImageRenderer", () => ({
  ImageRenderer: ({ url, alt, isThumbnail, ...props }: any) => (
    <img
      data-testid={isThumbnail ? "image-thumbnail" : "image-display"}
      src={url}
      alt={alt}
      data-props={JSON.stringify({ ...props, isThumbnail })}
    />
  ),
}));

vi.mock("@/components/media/MediaActions", () => ({
  MediaActions: ({ url, variant, className, copyLabel, downloadFileName }: any) => (
    <div
      data-testid="media-actions"
      data-url={url}
      data-variant={variant}
      data-class={className}
      data-copy-label={copyLabel}
      data-download-filename={downloadFileName}
    />
  ),
}));


const renderWithProviders = (component: React.ReactElement) => {
  return render(<TooltipProvider>{component}</TooltipProvider>);
};

describe("ImageContent", () => {
  const defaultProps = {
    url: "https://example.com/image.jpg",
    alt: "Test image",
    width: 800,
    height: 600,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with basic props", () => {
    renderWithProviders(<ImageContent {...defaultProps} />);

    expect(screen.getByTestId("media-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("image-thumbnail")).toBeInTheDocument();
    expect(screen.getByTestId("image-display")).toBeInTheDocument();
  });

  it("passes correct props to ImageRenderer thumbnail", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        thumbnail_size="xl"
        display_size="xxl"
        preload={true}
        objectFit="contain"
      />
    );

    const thumbnail = screen.getByTestId("image-thumbnail");
    const props = JSON.parse(thumbnail.getAttribute("data-props") || "{}");

    expect(props.thumbnail_size).toBe("xl");
    expect(props.display_size).toBe("xxl");
    expect(props.preload).toBe(true);
    expect(props.objectFit).toBe("contain");
    expect(props.isThumbnail).toBe(true);
  });

  it("passes correct props to ImageRenderer display", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        display_size="l"
      />
    );

    const display = screen.getByTestId("image-display");
    const props = JSON.parse(display.getAttribute("data-props") || "{}");

    expect(props.display_size).toBe("l");
    expect(props.isThumbnail).toBe(false);
  });

  it("shows controls when showControls is true", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        showControls={true}
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    expect(mediaActions).toHaveLength(2); // One for thumbnail controls, one for dialog actions
  });

  it("does not show thumbnail controls when showControls is false", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        showControls={false}
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    expect(mediaActions).toHaveLength(1); // Only dialog actions
  });

  it("passes correct MediaActions props for thumbnail controls", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        showControls={true}
        url="https://example.com/test-image.png"
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    const thumbnailActions = mediaActions[0]; // First one should be thumbnail controls

    expect(thumbnailActions.getAttribute("data-variant")).toBe("outline");
    expect(thumbnailActions.getAttribute("data-copy-label")).toBe("Image URL");
    expect(thumbnailActions.getAttribute("data-download-filename")).toBe("test-image.png");
  });

  it("passes correct MediaActions props for dialog actions", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        url="https://example.com/another-image.jpg"
      />
    );

    const mediaActions = screen.getAllByTestId("media-actions");
    const dialogActions = mediaActions[mediaActions.length - 1]; // Last one should be dialog actions

    expect(dialogActions.getAttribute("data-variant")).toBe("ghost");
    expect(dialogActions.getAttribute("data-copy-label")).toBe("Image URL");
    expect(dialogActions.getAttribute("data-download-filename")).toBe("another-image.jpg");
  });

  it("passes metadata to MediaDialog", () => {
    const metadata = { camera: "Canon EOS R5", iso: "400" };

    renderWithProviders(
      <ImageContent
        {...defaultProps}
        metadata={metadata}
      />
    );

    expect(screen.getByTestId("dialog-metadata")).toHaveTextContent(JSON.stringify(metadata));
  });

  it("passes description to MediaDialog", () => {
    const description = "A beautiful sunset over the mountains";

    renderWithProviders(
      <ImageContent
        {...defaultProps}
        description={description}
      />
    );

    expect(screen.getByTestId("dialog-description")).toHaveTextContent(description);
  });

  it("passes dimensions to MediaDialog", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        width={1920}
        height={1080}
      />
    );

    const dimensions = JSON.parse(screen.getByTestId("dialog-dimensions").textContent || "{}");
    expect(dimensions.width).toBe(1920);
    expect(dimensions.height).toBe(1080);
  });

  it("uses alt text as dialog title", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        alt="Custom alt text"
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Custom alt text");
  });

  it("uses default title when alt is not provided", () => {
    renderWithProviders(
      <ImageContent
        url="https://example.com/image.jpg"
      />
    );

    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Image Details");
  });

  it("applies custom className to trigger container", () => {
    renderWithProviders(
      <ImageContent
        {...defaultProps}
        className="custom-class"
      />
    );

    const trigger = screen.getByTestId("dialog-trigger");
    expect(trigger.firstChild).toHaveClass("custom-class");
  });

  it("handles mediaItem prop correctly", () => {
    const mediaItem = { id: "test-media-123" };

    renderWithProviders(
      <ImageContent
        {...defaultProps}
        mediaItem={mediaItem as any}
        showControls={true}
      />
    );

    // MediaActions should receive the mediaItem
    const mediaActions = screen.getAllByTestId("media-actions");
    mediaActions.forEach(action => {
      expect(action).toBeInTheDocument();
    });
  });

  it("uses default thumbnail and display sizes", () => {
    renderWithProviders(<ImageContent {...defaultProps} />);

    const thumbnail = screen.getByTestId("image-thumbnail");
    const display = screen.getByTestId("image-display");

    const thumbnailProps = JSON.parse(thumbnail.getAttribute("data-props") || "{}");
    const displayProps = JSON.parse(display.getAttribute("data-props") || "{}");

    expect(thumbnailProps.thumbnail_size).toBe("l");
    expect(displayProps.display_size).toBe("o");
  });

  it("uses default objectFit and preload values", () => {
    renderWithProviders(<ImageContent {...defaultProps} />);

    const thumbnail = screen.getByTestId("image-thumbnail");
    const props = JSON.parse(thumbnail.getAttribute("data-props") || "{}");

    expect(props.objectFit).toBe("contain");
    expect(props.preload).toBe(false);
  });
});
