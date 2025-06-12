import { vi } from 'vitest';
import { render, screen, fireEvent } from "@testing-library/react";
import ToggleSystemMessages from "../ToggleSystemMessages";

// Mock the tooltip since it uses React Portal which can be difficult to test
vi.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipContent: () => null,
}));

describe("ToggleSystemMessages", () => {
  const mockOnToggle = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with correct variant based on showTools prop", () => {
    const { rerender } = render(<ToggleSystemMessages showTools={false} onToggle={mockOnToggle} />);

    // When showTools is false, should have variant ghost
    const button = screen.getByRole("button");
    expect(button.className).toContain("hover:bg-accent");

    // Rerender with showTools=true
    rerender(<ToggleSystemMessages showTools={true} onToggle={mockOnToggle} />);

    // When showTools is true, should have variant default
    expect(button.className).toContain("bg-primary");
  });

  it("calls onToggle when button is clicked", () => {
    render(<ToggleSystemMessages showTools={false} onToggle={mockOnToggle} />);

    const button = screen.getByRole("button");
    fireEvent.click(button);

    expect(mockOnToggle).toHaveBeenCalledTimes(1);
  });

  it("renders the Bot icon", () => {
    render(<ToggleSystemMessages showTools={false} onToggle={mockOnToggle} />);

    // Check for the svg icon (Bot component renders as svg)
    const iconContainer = screen.getByRole("button").querySelector(".lucide-bot");
    expect(iconContainer).toBeInTheDocument();
  });

  it("renders with accessible screen reader text", () => {
    render(<ToggleSystemMessages showTools={false} onToggle={mockOnToggle} />);

    // Use getAllByText since we only care about the one with sr-only class
    const srElements = screen.getAllByText("Toggle System Messages");
    const srText = srElements.find(el => el.className.includes("sr-only"));
    expect(srText).toBeInTheDocument();
    expect(srText?.className).toContain("sr-only");
  });
});
