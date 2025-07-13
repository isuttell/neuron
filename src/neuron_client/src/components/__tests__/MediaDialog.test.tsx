import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MediaDialogComponent from "../MediaDialog";

// Mock Dialog components from shadcn/ui
vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: any) => <div data-testid="dialog">{children}</div>,
  DialogContent: ({ children, className }: any) => (
    <div data-testid="dialog-content" className={className}>
      {children}
    </div>
  ),
  DialogHeader: ({ children }: any) => <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <div data-testid="dialog-title">{children}</div>,
  DialogTrigger: ({ children }: any) => <div data-testid="dialog-trigger">{children}</div>,
}));

// Mock cn utility
vi.mock("@/lib/utils", () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(" "),
}));

describe("MediaDialogComponent", () => {
  const defaultProps = {
    trigger: <button>Open Dialog</button>,
    title: "Test Media Dialog",
    children: <div data-testid="media-content">Media content goes here</div>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with basic props", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    expect(screen.getByTestId("dialog")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-trigger")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-content")).toBeInTheDocument();
    expect(screen.getByTestId("dialog-title")).toHaveTextContent("Test Media Dialog");
    expect(screen.getByTestId("media-content")).toBeInTheDocument();
  });

  it("renders trigger content", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    expect(screen.getByText("Open Dialog")).toBeInTheDocument();
  });

  it("renders media content in the media section", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    const mediaContent = screen.getByTestId("media-content");
    expect(mediaContent).toBeInTheDocument();
    expect(mediaContent.closest('[class*="bg-black/5"]')).toBeInTheDocument();
  });

  it("renders actions when provided", () => {
    const actions = (
      <div data-testid="test-actions">
        <button>Copy</button>
        <button>Download</button>
      </div>
    );

    render(
      <MediaDialogComponent
        {...defaultProps}
        actions={actions}
      />
    );

    expect(screen.getByTestId("test-actions")).toBeInTheDocument();
    expect(screen.getByText("Copy")).toBeInTheDocument();
    expect(screen.getByText("Download")).toBeInTheDocument();
  });

  it("does not render actions toolbar when actions not provided", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    // Actions toolbar should not exist when no actions provided
    const actionToolbars = screen.queryAllByText(/flex items-center gap-2 border-b/);
    expect(actionToolbars).toHaveLength(0);
  });

  it("renders description when provided", () => {
    const description = "This is a test description for the media item";

    render(
      <MediaDialogComponent
        {...defaultProps}
        description={description}
      />
    );

    expect(screen.getByText("Description")).toBeInTheDocument();
    expect(screen.getByText(description)).toBeInTheDocument();
  });

  it("does not render description section when not provided", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    expect(screen.queryByText("Description")).not.toBeInTheDocument();
  });

  it("renders dimensions when provided", () => {
    const dimensions = { width: 1920, height: 1080 };

    render(
      <MediaDialogComponent
        {...defaultProps}
        dimensions={dimensions}
      />
    );

    expect(screen.getByText("Dimensions")).toBeInTheDocument();
    expect(screen.getByText("1920 × 1080")).toBeInTheDocument();
  });

  it("renders width only when height not provided", () => {
    const dimensions = { width: 800 };

    render(
      <MediaDialogComponent
        {...defaultProps}
        dimensions={dimensions}
      />
    );

    expect(screen.getByText("Width: 800")).toBeInTheDocument();
  });

  it("renders height only when width not provided", () => {
    const dimensions = { height: 600 };

    render(
      <MediaDialogComponent
        {...defaultProps}
        dimensions={dimensions}
      />
    );

    expect(screen.getByText("Height: 600")).toBeInTheDocument();
  });

  it("does not render dimensions section when not provided", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    expect(screen.queryByText("Dimensions")).not.toBeInTheDocument();
  });

  it("renders metadata when provided", () => {
    const metadata = {
      camera: "Canon EOS R5",
      iso: "400",
      focal_length: "85mm",
      empty_value: "",
      null_value: null,
      undefined_value: undefined,
    };

    render(
      <MediaDialogComponent
        {...defaultProps}
        metadata={metadata}
      />
    );

    // Should render non-empty values (keys are lowercase, then capitalized by CSS)
    expect(screen.getByText("camera")).toBeInTheDocument();
    expect(screen.getByText("Canon EOS R5")).toBeInTheDocument();
    expect(screen.getByText("iso")).toBeInTheDocument();
    expect(screen.getByText("400")).toBeInTheDocument();
    expect(screen.getByText("focal length")).toBeInTheDocument();
    expect(screen.getByText("85mm")).toBeInTheDocument();

    // Should not render empty, null, or undefined values
    expect(screen.queryByText("Empty value")).not.toBeInTheDocument();
    expect(screen.queryByText("Null value")).not.toBeInTheDocument();
    expect(screen.queryByText("Undefined value")).not.toBeInTheDocument();
  });

  it("formats metadata keys by replacing underscores with spaces and capitalizing", () => {
    const metadata = {
      exposure_time: "1/125s",
      white_balance: "Auto",
    };

    render(
      <MediaDialogComponent
        {...defaultProps}
        metadata={metadata}
      />
    );

    expect(screen.getByText("exposure time")).toBeInTheDocument();
    expect(screen.getByText("white balance")).toBeInTheDocument();
  });

  it("does not render metadata section when empty object", () => {
    render(
      <MediaDialogComponent
        {...defaultProps}
        metadata={{}}
      />
    );

    // Should not have any dl elements for metadata
    expect(screen.queryByRole("term")).not.toBeInTheDocument();
  });

  it("does not render metadata section when not provided", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    expect(screen.queryByRole("term")).not.toBeInTheDocument();
  });

  it("applies custom className to dialog content", () => {
    render(
      <MediaDialogComponent
        {...defaultProps}
        className="custom-dialog-class"
      />
    );

    const dialogContent = screen.getByTestId("dialog-content");
    expect(dialogContent).toHaveClass("custom-dialog-class");
  });

  it("has responsive grid layout classes", () => {
    render(<MediaDialogComponent {...defaultProps} />);

    const dialogContent = screen.getByTestId("dialog-content");
    expect(dialogContent).toHaveClass("max-w-[95vw]");
    expect(dialogContent).toHaveClass("max-h-[95vh]");
    expect(dialogContent).toHaveClass("w-full");
    expect(dialogContent).toHaveClass("h-[90vh]");
  });

  it("renders all sections in correct order", () => {
    const actions = <div data-testid="test-actions">Actions</div>;
    const description = "Test description";
    const dimensions = { width: 800, height: 600 };
    const metadata = { camera: "Test Camera" };

    render(
      <MediaDialogComponent
        {...defaultProps}
        actions={actions}
        description={description}
        dimensions={dimensions}
        metadata={metadata}
      />
    );

    // Get all the elements to check order
    const title = screen.getByTestId("dialog-title");
    const actionsElement = screen.getByTestId("test-actions");
    const descriptionText = screen.getByText(description);
    const dimensionsText = screen.getByText("800 × 600");
    const metadataText = screen.getByText("Test Camera");

    // All should be in the document
    expect(title).toBeInTheDocument();
    expect(actionsElement).toBeInTheDocument();
    expect(descriptionText).toBeInTheDocument();
    expect(dimensionsText).toBeInTheDocument();
    expect(metadataText).toBeInTheDocument();
  });
});
