import { render, screen } from "@testing-library/react";
import TokenChart from "../TokenChart";
import { ChartConfig } from "@/components/ui/chart";

// Mock the recharts library
jest.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  XAxis: () => <div data-testid="x-axis" />,
  Bar: () => <div data-testid="bar" />,
}));

// Mock the chart UI components
jest.mock("@/components/ui/chart", () => ({
  ChartConfig: jest.fn(),
  ChartContainer: ({
    children,
    config,
  }: {
    children: React.ReactNode;
    config: ChartConfig;
  }) => (
    <div data-testid="chart-container" data-config={JSON.stringify(config)}>
      {children}
    </div>
  ),
  ChartTooltip: ({
    children,
    content,
  }: {
    children?: React.ReactNode;
    content: React.ReactNode;
  }) => (
    <div data-testid="chart-tooltip">
      {content}
      {children}
    </div>
  ),
  ChartTooltipContent: () => <div data-testid="chart-tooltip-content" />,
}));

describe("TokenChart", () => {
  // Sample message data for testing
  const messages = [
    {
      usage_metadata: {
        input_tokens: 100,
        output_tokens: 200,
        total_tokens: 300,
      },
    },
    {
      usage_metadata: {
        input_tokens: 150,
        output_tokens: 250,
        total_tokens: 400,
      },
    },
    // Message without usage_metadata should be filtered out
    {},
  ];

  it("renders the chart container with proper config", () => {
    render(<TokenChart messages={messages} />);

    const container = screen.getByTestId("chart-container");
    expect(container).toBeInTheDocument();

    // Verify the config is passed correctly
    const configData = JSON.parse(container.getAttribute("data-config") || "{}");
    expect(configData).toHaveProperty("input");
    expect(configData).toHaveProperty("output");
    expect(configData.input.label).toBe("Input Tokens");
    expect(configData.output.label).toBe("Output Tokens");
  });

  it("renders the chart components", () => {
    render(<TokenChart messages={messages} />);

    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    expect(screen.getByTestId("cartesian-grid")).toBeInTheDocument();
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
    expect(screen.getByTestId("chart-tooltip")).toBeInTheDocument();
    expect(screen.getByTestId("chart-tooltip-content")).toBeInTheDocument();
    expect(screen.getByTestId("bar")).toBeInTheDocument();
  });

  it("filters out messages without usage_metadata", () => {
    // Mock console.log to verify the data being passed to the chart
    const originalConsoleLog = console.log;
    const mockConsoleLog = jest.fn();
    console.log = mockConsoleLog;

    render(<TokenChart messages={messages} />);

    // Should only log 2 items (filtering out the empty message)
    expect(mockConsoleLog).toHaveBeenCalledTimes(1);
    const loggedData = mockConsoleLog.mock.calls[0][0];
    expect(loggedData).toHaveLength(2);

    // Restore original console.log
    console.log = originalConsoleLog;
  });

  it("converts the message data to the correct format for the chart", () => {
    // Mock console.log to verify the data transformation
    const originalConsoleLog = console.log;
    const mockConsoleLog = jest.fn();
    console.log = mockConsoleLog;

    render(<TokenChart messages={messages} />);

    // Check the transformed data structure
    const transformedData = mockConsoleLog.mock.calls[0][0];
    expect(transformedData[0]).toEqual({
      name: "AI Msg 1",
      input: 100,
      output: 200,
      total: 300,
    });
    expect(transformedData[1]).toEqual({
      name: "AI Msg 2",
      input: 150,
      output: 250,
      total: 400,
    });

    // Restore original console.log
    console.log = originalConsoleLog;
  });

  it("handles empty messages array", () => {
    render(<TokenChart messages={[]} />);

    // Should still render the chart components, just with empty data
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    expect(screen.getByTestId("cartesian-grid")).toBeInTheDocument();
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
  });

  it("handles undefined token values", () => {
    const messagesWithUndefinedValues = [
      {
        usage_metadata: {
          // Missing input_tokens
          output_tokens: 200,
          total_tokens: 200,
        },
      },
      {
        usage_metadata: {
          input_tokens: 150,
          // Missing output_tokens
          total_tokens: 150,
        },
      },
    ];

    // Mock console.log to verify the data transformation
    const originalConsoleLog = console.log;
    const mockConsoleLog = jest.fn();
    console.log = mockConsoleLog;

    render(<TokenChart messages={messagesWithUndefinedValues} />);

    // Check that missing values are replaced with 0
    const transformedData = mockConsoleLog.mock.calls[0][0];
    expect(transformedData[0].input).toBe(0);
    expect(transformedData[1].output).toBe(0);

    // Restore original console.log
    console.log = originalConsoleLog;
  });
});
