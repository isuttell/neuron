import { useEffect, memo } from "react";
import { Label, Pie, PieChart } from "recharts";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { useAppDispatch, useAppSelector } from "@/hooks";
import { getTotalInputTokens, getTotalOutputTokens } from "@/slices/appSlice";

const chartConfig = {
  input: {
    label: "Input",
    color: "hsl(var(--chart-1))",
  },
  output: {
    label: "Output",
    color: "hsl(var(--chart-2))",
  },
} satisfies ChartConfig;

function formatNumber(num: number): string {
  if (num < 1000) {
    return num.toString();
  }
  const units = ["k", "M ", "B", "T"];
  const order = Math.floor(Math.log10(num) / 3);
  const unitName = units[order - 1];
  const shortNum = parseFloat((num / Math.pow(1000, order)).toFixed(1));
  return `${shortNum}${unitName}`;
}

export function TotalTokenCount() {
  const inputTokens = useAppSelector(getTotalInputTokens);
  const outputTokens = useAppSelector(getTotalOutputTokens);
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch({
      type: "socket/GetTokenStats",
    });
  }, []);

  return (
    <ChartContainer
      config={chartConfig}
      className="mx-auto aspect-square max-h-[250px] w-full"
    >
      <PieChart>
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent hideLabel />}
        />
        <Pie
          data={[
            { type: "input", value: inputTokens, fill: "var(--color-input)" },
            {
              type: "output",
              value: outputTokens,
              fill: "var(--color-output)",
            },
          ]}
          dataKey="value"
          nameKey="type"
          innerRadius={60}
          strokeWidth={5}
        >
          <Label
            content={({ viewBox }) => {
              if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                return (
                  <text
                    x={viewBox.cx}
                    y={viewBox.cy}
                    textAnchor="middle"
                    dominantBaseline="middle"
                  >
                    <tspan
                      x={viewBox.cx}
                      y={viewBox.cy}
                      className="fill-foreground text-3xl font-bold"
                    >
                      {formatNumber(Math.max(0, inputTokens + outputTokens))}
                    </tspan>
                    <tspan
                      x={viewBox.cx}
                      y={(viewBox.cy || 0) + 24}
                      className="fill-muted-foreground"
                    >
                      Tokens
                    </tspan>
                  </text>
                );
              }
            }}
          />
        </Pie>
      </PieChart>
    </ChartContainer>
  );
}

export default memo(TotalTokenCount);
