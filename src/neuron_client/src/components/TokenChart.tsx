import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

interface TokenChartProps {
  messages: Array<{
    usage_metadata?: {
      input_tokens?: number;
      output_tokens?: number;
      total_tokens?: number;
    };
  }>;
}

const chartConfig = {
  input: {
    label: "Input Tokens",
    color: "hsl(var(--chart-1))",
  },
  output: {
    label: "Output Tokens",
    color: "hsl(var(--chart-2))",
  },
} satisfies ChartConfig;

const TokenChart: React.FC<TokenChartProps> = ({ messages }) => {
  const tokenData = messages
    .filter((message) => message.usage_metadata)
    .map((message, index) => ({
      name: `AI Msg ${index + 1}`,
      input: message.usage_metadata?.input_tokens || 0,
      output: message.usage_metadata?.output_tokens || 0,
      total: message.usage_metadata?.total_tokens || 0,
    }));
  console.log(tokenData);
  return (
    <ChartContainer config={chartConfig}>
      <BarChart data={tokenData}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="name"
          tickLine={false}
          tickMargin={10}
          axisLine={false}
        />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent indicator="dashed" />}
        />
        <Bar dataKey="total" fill="green" radius={4} />
      </BarChart>
    </ChartContainer>
  );
};

export default TokenChart;
