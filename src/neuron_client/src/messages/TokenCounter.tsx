import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return (num / 1_000_000).toFixed(1) + "m";
  } else if (num >= 1_000) {
    return (num / 1_000).toFixed(1) + "k";
  }
  return num.toString();
}

export default function TokenCounter({
  input_tokens,
  total_tokens,
  output_tokens,
}: {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}) {
  const anthropicEstCost =
    input_tokens / 3_000_000 + output_tokens / 15_000_000;
  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger>
        <div className="flex m-2.5">
          <div className="w-[100px] h-[20px] bg-secondary rounded-full relative">
            <div
              className="bg-primary absolute top-0 left-0 h-full rounded-full"
              style={{ width: (input_tokens / total_tokens) * 100 + "%" }}
            />
            <div className="text-primary-foreground font-bold absolute top-0 left-0 w-full h-full flex items-center justify-center">
              {formatNumber(total_tokens)}
            </div>
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <table className="min-w-full">
          <tbody>
            <tr className="border-b">
              <td className="text-sm font-bold">Input</td>
              <td className="text-sm text-right">
                {input_tokens.toLocaleString()}
              </td>
            </tr>
            <tr className="border-b">
              <td className="text-sm font-bold">Output</td>
              <td className="text-sm text-right">
                {output_tokens.toLocaleString()}
              </td>
            </tr>
            <tr>
              <td className="text-sm font-bold">Total</td>
              <td className="text-sm text-right">
                {total_tokens.toLocaleString()}
              </td>
            </tr>
            <tr>
              <td className="text-sm font-bold">Est. Cost</td>
              <td className="text-sm text-right">
                ${anthropicEstCost.toFixed(2)}
              </td>
            </tr>
          </tbody>
        </table>
      </TooltipContent>
    </Tooltip>
  );
}
