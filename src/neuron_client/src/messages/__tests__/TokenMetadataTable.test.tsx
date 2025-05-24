import { render, screen } from "@testing-library/react";
import TokenMetadataTable from "../TokenMetadataTable";

describe("TokenMetadataTable", () => {
  const baseProps = {
    input_tokens: 1000,
    output_tokens: 500,
    total_tokens: 1500,
  };

  it("renders basic token information correctly", () => {
    render(<TokenMetadataTable {...baseProps} />);

    expect(screen.getByText("Input")).toBeInTheDocument();
    expect(screen.getByText("1,000")).toBeInTheDocument();

    expect(screen.getByText("Output")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();

    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("1,500")).toBeInTheDocument();
  });

  it("formats large numbers with commas", () => {
    const largeProps = {
      input_tokens: 1234567,
      output_tokens: 987654,
      total_tokens: 2222221,
    };

    render(<TokenMetadataTable {...largeProps} />);

    expect(screen.getByText("1,234,567")).toBeInTheDocument();
    expect(screen.getByText("987,654")).toBeInTheDocument();
    expect(screen.getByText("2,222,221")).toBeInTheDocument();
  });

  it("does not render cache details when input_token_details is not provided", () => {
    render(<TokenMetadataTable {...baseProps} />);

    expect(screen.queryByText("Cache Creation")).not.toBeInTheDocument();
    expect(screen.queryByText("Cache Read")).not.toBeInTheDocument();
  });

  it("does not render cache details when cache values are zero", () => {
    const propsWithZeroCache = {
      ...baseProps,
      input_token_details: {
        cache_creation: 0,
        cache_read: 0,
      },
    };

    render(<TokenMetadataTable {...propsWithZeroCache} />);

    expect(screen.queryByText("Cache Creation")).not.toBeInTheDocument();
    expect(screen.queryByText("Cache Read")).not.toBeInTheDocument();
  });

  it("renders cache creation when value is greater than zero", () => {
    const propsWithCacheCreation = {
      ...baseProps,
      input_token_details: {
        cache_creation: 13436,
        cache_read: 0,
      },
    };

    render(<TokenMetadataTable {...propsWithCacheCreation} />);

    expect(screen.getByText("Cache Creation")).toBeInTheDocument();
    expect(screen.getByText("13,436")).toBeInTheDocument();
    expect(screen.queryByText("Cache Read")).not.toBeInTheDocument();
  });

  it("renders cache read when value is greater than zero", () => {
    const propsWithCacheRead = {
      ...baseProps,
      input_token_details: {
        cache_creation: 0,
        cache_read: 5000,
      },
    };

    render(<TokenMetadataTable {...propsWithCacheRead} />);

    expect(screen.queryByText("Cache Creation")).not.toBeInTheDocument();
    expect(screen.getByText("Cache Read")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
  });

  it("renders both cache creation and cache read when both are greater than zero", () => {
    const propsWithBothCache = {
      ...baseProps,
      input_token_details: {
        cache_creation: 13436,
        cache_read: 2500,
      },
    };

    render(<TokenMetadataTable {...propsWithBothCache} />);

    expect(screen.getByText("Cache Creation")).toBeInTheDocument();
    expect(screen.getByText("13,436")).toBeInTheDocument();
    expect(screen.getByText("Cache Read")).toBeInTheDocument();
    expect(screen.getByText("2,500")).toBeInTheDocument();
  });

  it("applies custom className correctly", () => {
    const { container } = render(
      <TokenMetadataTable {...baseProps} className="custom-class" />
    );

    const table = container.querySelector("table");
    expect(table).toHaveClass("min-w-full", "custom-class");
  });

  it("renders undefined cache values without crashing", () => {
    const propsWithUndefinedCache = {
      ...baseProps,
      input_token_details: {
        cache_creation: undefined,
        cache_read: undefined,
      },
    };

    render(<TokenMetadataTable {...propsWithUndefinedCache} />);

    expect(screen.getByText("Input")).toBeInTheDocument();
    expect(screen.getByText("Output")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.queryByText("Cache Creation")).not.toBeInTheDocument();
    expect(screen.queryByText("Cache Read")).not.toBeInTheDocument();
  });

  it("has correct table structure with proper borders", () => {
    const propsWithCache = {
      ...baseProps,
      input_token_details: {
        cache_creation: 1000,
        cache_read: 500,
      },
    };

    const { container } = render(<TokenMetadataTable {...propsWithCache} />);

    const rows = container.querySelectorAll("tr");
    expect(rows).toHaveLength(5); // Input, Output, Total, Cache Creation, Cache Read

    // Check that appropriate rows have border-b class
    expect(rows[0]).toHaveClass("border-b"); // Input row
    expect(rows[1]).toHaveClass("border-b"); // Output row
    expect(rows[2]).toHaveClass("border-b"); // Total row (with cache details)
    expect(rows[3]).toHaveClass("border-b"); // Cache Creation row
    expect(rows[4]).not.toHaveClass("border-b"); // Cache Read row (last)
  });

  it("has correct table structure without cache details", () => {
    const { container } = render(<TokenMetadataTable {...baseProps} />);

    const rows = container.querySelectorAll("tr");
    expect(rows).toHaveLength(3); // Input, Output, Total

    // Check that Total row doesn't have border when no cache details
    expect(rows[0]).toHaveClass("border-b"); // Input row
    expect(rows[1]).toHaveClass("border-b"); // Output row
    expect(rows[2]).not.toHaveClass("border-b"); // Total row (last, no cache)
  });

  it("handles zero token values correctly", () => {
    const zeroProps = {
      input_tokens: 0,
      output_tokens: 0,
      total_tokens: 0,
    };

    render(<TokenMetadataTable {...zeroProps} />);

    const zeros = screen.getAllByText("0");
    expect(zeros).toHaveLength(3); // One for each token type
  });
});
