import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatNumber } from "../utils/numberFormat";
import TokenMetadataTable from "./TokenMetadataTable";

export default function TokenCounter({
  input_tokens,
  total_tokens,
  output_tokens,
}: {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}) {
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
        <TokenMetadataTable
          input_tokens={input_tokens}
          output_tokens={output_tokens}
          total_tokens={total_tokens}
        />
      </TooltipContent>
    </Tooltip>
  );
}
