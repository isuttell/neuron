import { vi } from 'vitest';
import { render, screen } from "@testing-library/react";
import TokenCounter from "../TokenCounter";
import { formatNumber } from "../../utils/numberFormat";

// Mock formatNumber function
vi.mock("../../utils/numberFormat", () => ({
  formatNumber: vi.fn(),
}));

// Mock the TooltipContent component to make it always visible in tests
vi.mock("@/components/ui/tooltip", () => {
  const actual = vi.importActual("@/components/ui/tooltip");
  return {
    ...actual,
    TooltipContent: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="tooltip-content">{children}</div>
    ),
    TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>
  };
});

// Mock TokenMetadataTable component
vi.mock("../TokenMetadataTable", () => ({
  default: function MockTokenMetadataTable({
    input_tokens,
    output_tokens,
    total_tokens,
  }: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  }) {
    return (
      <div data-testid="token-metadata-table">
        <div data-testid="input-tokens">{input_tokens}</div>
        <div data-testid="output-tokens">{output_tokens}</div>
        <div data-testid="total-tokens">{total_tokens}</div>
      </div>
    );
  }
}));

describe("TokenCounter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default implementation for formatNumber
    (formatNumber as vi.Mock).mockImplementation((num) => num.toString());
  });

  it("renders with correct token values", () => {
    const props = {
      input_tokens: 100,
      output_tokens: 150,
      total_tokens: 250,
    };

    (formatNumber as vi.Mock).mockReturnValue("250");

    render(<TokenCounter {...props} />);

    // Check that the formatted total tokens value is displayed in the progress bar
    const progressText = screen.getAllByText("250").find(element =>
      element.parentElement?.className.includes("bg-secondary")
    );
    expect(progressText).toBeDefined();

    // Verify formatNumber was called with the correct value
    expect(formatNumber).toHaveBeenCalledWith(250);
  });

  it("calculates the correct percentage width for progress bar", () => {
    const props = {
      input_tokens: 200,
      output_tokens: 300,
      total_tokens: 500,
    };

    (formatNumber as vi.Mock).mockReturnValue("500");

    const { container } = render(<TokenCounter {...props} />);

    // Get the progress bar element
    const progressBar = container.querySelector(".bg-primary");
    expect(progressBar).not.toBeNull();

    // Check that the width is roughly 40% (exact formatting may vary)
    const style = progressBar?.getAttribute("style");
    expect(style).toBeDefined();
    expect(style).toContain("width: 40%");
  });

  it("passes correct props to TokenMetadataTable", () => {
    const props = {
      input_tokens: 150,
      output_tokens: 250,
      total_tokens: 400,
    };

    render(<TokenCounter {...props} />);

    // Now we can find the TokenMetadataTable which is always rendered
    // because we've mocked the TooltipContent to be visible
    const tooltipContent = screen.getByTestId("tooltip-content");
    expect(tooltipContent).toBeInTheDocument();

    // The rendered TokenMetadataTable should receive the correct props
    const inputTokens = screen.getByTestId("input-tokens");
    const outputTokens = screen.getByTestId("output-tokens");
    const totalTokens = screen.getByTestId("total-tokens");

    expect(inputTokens.textContent).toBe("150");
    expect(outputTokens.textContent).toBe("250");
    expect(totalTokens.textContent).toBe("400");
  });
});
