import { vi } from 'vitest';
import { render, screen } from "@testing-library/react";
import TokenChart from "../TokenChart";
import { ChartConfig } from "@/components/ui/chart";

// Mock the recharts library
vi.mock("recharts", () => ({
  BarChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)}>
      {children}
    </div>
  ),
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  XAxis: () => <div data-testid="x-axis" />,
  Bar: () => <div data-testid="bar" />,
}));

// Mock the chart UI components
vi.mock("@/components/ui/chart", () => ({
  ChartConfig: vi.fn(),
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
    expect(configData).toHaveProperty("total");
    expect(configData.input.label).toBe("Input Tokens");
    expect(configData.output.label).toBe("Output Tokens");
    expect(configData.total.label).toBe("Total Tokens");
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

  it("filters out messages without usage_metadata and transforms data correctly", () => {
    render(<TokenChart messages={messages} />);

    // Get the chart data from the BarChart component
    const barChart = screen.getByTestId("bar-chart");
    const chartData = JSON.parse(barChart.getAttribute("data-chart-data") || "[]");

    // Should only include 2 items (filtering out the empty message)
    expect(chartData).toHaveLength(2);

    // Check the transformed data structure
    expect(chartData[0]).toEqual({
      name: "AI Msg 1",
      input: 100,
      output: 200,
      total: 300,
    });
    expect(chartData[1]).toEqual({
      name: "AI Msg 2",
      input: 150,
      output: 250,
      total: 400,
    });
  });

  it("handles empty messages array", () => {
    render(<TokenChart messages={[]} />);

    // Should still render the chart components, just with empty data
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    expect(screen.getByTestId("cartesian-grid")).toBeInTheDocument();
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();

    // Verify empty data is passed to the chart
    const barChart = screen.getByTestId("bar-chart");
    const chartData = JSON.parse(barChart.getAttribute("data-chart-data") || "[]");
    expect(chartData).toHaveLength(0);
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

    render(<TokenChart messages={messagesWithUndefinedValues} />);

    // Get the chart data from the BarChart component
    const barChart = screen.getByTestId("bar-chart");
    const chartData = JSON.parse(barChart.getAttribute("data-chart-data") || "[]");

    // Check that missing values are replaced with 0
    expect(chartData[0].input).toBe(0);
    expect(chartData[0].output).toBe(200);
    expect(chartData[0].total).toBe(200);

    expect(chartData[1].input).toBe(150);
    expect(chartData[1].output).toBe(0);
    expect(chartData[1].total).toBe(150);
  });

  it("generates correct AI message names", () => {
    render(<TokenChart messages={messages} />);

    const barChart = screen.getByTestId("bar-chart");
    const chartData = JSON.parse(barChart.getAttribute("data-chart-data") || "[]");

    expect(chartData[0].name).toBe("AI Msg 1");
    expect(chartData[1].name).toBe("AI Msg 2");
  });
});
