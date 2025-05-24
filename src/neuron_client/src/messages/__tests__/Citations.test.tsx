import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import Citations from "../Citations";
import { Citation } from "@/slices/messagesSlice";

describe("Citations", () => {
  const mockCitations: Citation[] = [
    {
      type: "char_location",
      cited_text: "The grass is green.",
      document_index: 0,
      document_title: "My Document",
      start_char_index: 0,
      end_char_index: 20,
    },
    {
      type: "char_location",
      cited_text: "The sky is blue.",
      document_index: 0,
      document_title: "My Document",
      start_char_index: 20,
      end_char_index: 36,
    },
    {
      type: "char_location",
      cited_text: "Water is essential for life.",
      document_index: 1,
      document_title: "Science Facts",
      start_char_index: 0,
      end_char_index: 28,
    },
  ];

  it("should not render when citations array is empty", () => {
    const { container } = render(<Citations citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("should not render when citations is undefined", () => {
    const { container } = render(<Citations citations={undefined as unknown as Citation[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("should render collapsed by default", () => {
    render(<Citations citations={mockCitations} />);

    expect(screen.getByText("Citations (3)")).toBeInTheDocument();
    expect(screen.queryByText("The grass is green.")).not.toBeInTheDocument();
  });

  it("should expand when clicked", () => {
    render(<Citations citations={mockCitations} />);

    const trigger = screen.getByText("Citations (3)").closest("div");
    fireEvent.click(trigger!);

    expect(screen.getByText('"The grass is green."')).toBeInTheDocument();
    expect(screen.getByText('"The sky is blue."')).toBeInTheDocument();
    expect(screen.getByText('"Water is essential for life."')).toBeInTheDocument();
  });

  it("should group citations by document", () => {
    render(<Citations citations={mockCitations} />);

    const trigger = screen.getByText("Citations (3)").closest("div");
    fireEvent.click(trigger!);

    // Check for document titles
    expect(screen.getByText("My Document")).toBeInTheDocument();
    expect(screen.getByText("Science Facts")).toBeInTheDocument();

    // Check citation counts per document
    expect(screen.getByText("2 citations")).toBeInTheDocument();
    expect(screen.getByText("1 citation")).toBeInTheDocument();
  });

  it("should display character ranges", () => {
    render(<Citations citations={mockCitations} />);

    const trigger = screen.getByText("Citations (3)").closest("div");
    fireEvent.click(trigger!);

    expect(screen.getByText("Characters 0-20")).toBeInTheDocument();
    expect(screen.getByText("Characters 20-36")).toBeInTheDocument();
    expect(screen.getByText("Characters 0-28")).toBeInTheDocument();
  });

  it("should toggle expansion state", () => {
    render(<Citations citations={mockCitations} />);

    const trigger = screen.getByText("Citations (3)").closest("div");

    // Expand
    fireEvent.click(trigger!);
    expect(screen.getByText('"The grass is green."')).toBeInTheDocument();

    // Collapse
    fireEvent.click(trigger!);
    expect(screen.queryByText('"The grass is green."')).not.toBeInTheDocument();
  });

  it("should render with proper styling classes", () => {
    render(<Citations citations={mockCitations} />);

    const container = screen.getByText("Citations (3)").closest(".mt-4");
    expect(container).toHaveClass("mt-4", "border", "rounded-lg", "bg-muted/30");
  });
});
