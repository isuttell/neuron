import { vi } from 'vitest';
import { render, screen } from "@testing-library/react";
import { StatusMessage } from "../StatusMessage";

// Mock the cn utility function
vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

describe("StatusMessage", () => {
  it("renders a single status correctly", () => {
    render(<StatusMessage status="thinking" />);

    expect(screen.getByText("Thinking")).toBeInTheDocument();
  });

  it("renders multiple statuses correctly", () => {
    render(<StatusMessage status="thinking,tools" />);

    expect(screen.getByText("Thinking")).toBeInTheDocument();
    expect(screen.getByText("Tools")).toBeInTheDocument();
  });

  it("sorts statuses with thinking and tools first", () => {
    const { container } = render(<StatusMessage status="update_title,thinking,tools" />);

    // Check that the order is correct (first child is "Thinking", second is "Tools", third is "Title")
    const statusDivs = container.querySelectorAll(".flex.flex-row div");
    expect(statusDivs[0].textContent).toBe("Thinking");
    expect(statusDivs[1].textContent).toBe("Tools");
    expect(statusDivs[2].textContent).toBe("Title");
  });

  it("transforms unknown statuses with proper capitalization", () => {
    render(<StatusMessage status="custom_status" />);

    expect(screen.getByText("Custom Status")).toBeInTheDocument();
  });

  it("applies custom class names", () => {
    const { container } = render(
      <StatusMessage
        status="thinking"
        className="custom-class"
        tagClassName="tag-class"
      />
    );

    // Check container class
    expect(container.firstChild).toHaveClass("flex");
    expect(container.firstChild).toHaveClass("flex-row");
    expect(container.firstChild).toHaveClass("custom-class");

    // Check tag class
    const tag = screen.getByText("Thinking");
    expect(tag).toHaveClass("tag-class");
  });

  it("handles TTS capitalization properly", () => {
    render(<StatusMessage status="tts_processing" />);

    expect(screen.getByText("TTS Processing")).toBeInTheDocument();
  });

  it("removes duplicate statuses", () => {
    render(<StatusMessage status="thinking,thinking,tools" />);

    // Even though "thinking" appears twice, it should only render once
    const thinkingElements = screen.getAllByText("Thinking");
    expect(thinkingElements.length).toBe(1);

    expect(screen.getByText("Tools")).toBeInTheDocument();
  });
});
