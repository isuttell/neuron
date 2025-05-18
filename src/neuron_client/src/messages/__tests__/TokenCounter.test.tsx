import { render, screen } from "@testing-library/react";
import TokenCounter from "../TokenCounter";
import { formatNumber } from "../../utils/numberFormat";

// Mock the formatNumber function to make testing easier
jest.mock("../../utils/numberFormat", () => ({
  formatNumber: jest.fn(),
}));

// We need to spy on TooltipContent rendered content rather than mocking TokenMetadataTable
jest.mock("@/components/ui/tooltip", () => {
  const actual = jest.requireActual("@/components/ui/tooltip");
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

// Mock TokenMetadataTable as a simple component
jest.mock("../TokenMetadataTable", () => {
  return function MockTokenMetadataTable(props: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  }) {
    return (
      <div data-testid="token-metadata-table">
        <div data-testid="input-tokens">{props.input_tokens}</div>
        <div data-testid="output-tokens">{props.output_tokens}</div>
        <div data-testid="total-tokens">{props.total_tokens}</div>
      </div>
    );
  };
});

describe("TokenCounter", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock implementation for formatNumber
    (formatNumber as jest.Mock).mockImplementation((num) => num.toString());
  });

  it("renders with correct token values", () => {
    const props = {
      input_tokens: 100,
      output_tokens: 150,
      total_tokens: 250,
    };

    (formatNumber as jest.Mock).mockReturnValue("250");

    render(<TokenCounter {...props} />);

    // Check that the formatted total tokens value is displayed in the progress bar
    expect(screen.getAllByText("250").length).toBeGreaterThan(0);

    // Verify the mocked TokenMetadataTable has been rendered with the correct props
    expect(screen.getByTestId("token-metadata-table")).toBeInTheDocument();
    expect(screen.getByTestId("input-tokens").textContent).toBe("100");
    expect(screen.getByTestId("output-tokens").textContent).toBe("150");
    expect(screen.getByTestId("total-tokens").textContent).toBe("250");
  });

  it("calculates the correct percentage width for progress bar", () => {
    const props = {
      input_tokens: 200,
      output_tokens: 300,
      total_tokens: 500,
    };

    (formatNumber as jest.Mock).mockReturnValue("500");

    render(<TokenCounter {...props} />);

    // Get the progress bar element
    const progressBar = document.querySelector(".bg-primary");
    expect(progressBar).not.toBeNull();

    // Check that the width is roughly 40% (exact formatting may vary)
    const style = progressBar?.getAttribute("style");
    expect(style).toBeDefined();
    expect(style).toContain("width: 40%"); // Just check that it contains the correct width
  });

  it("calls formatNumber with the correct total tokens value", () => {
    const props = {
      input_tokens: 1500,
      output_tokens: 2500,
      total_tokens: 4000,
    };

    render(<TokenCounter {...props} />);

    // Check that formatNumber was called with the total tokens value
    expect(formatNumber).toHaveBeenCalledWith(4000);
  });
});
