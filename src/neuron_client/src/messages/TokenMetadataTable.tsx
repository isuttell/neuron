import { cn } from "@/lib/utils";

interface TokenMetadataTableProps {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  className?: string;
}

export default function TokenMetadataTable({
  input_tokens,
  output_tokens,
  total_tokens,
  className = "",
}: TokenMetadataTableProps) {
  return (
    <table className={cn("min-w-full", className)}>
      <tbody>
        <tr className="border-b">
          <td className="text-sm font-bold text-right px-4 py-2">Input</td>
          <td className="text-sm text-right px-4 py-2">
            {input_tokens.toLocaleString()}
          </td>
        </tr>
        <tr className="border-b">
          <td className="text-sm font-bold text-right px-4 py-2">Output</td>
          <td className="text-sm text-right px-4 py-2">
            {output_tokens.toLocaleString()}
          </td>
        </tr>
        <tr>
          <td className="text-sm font-bold text-right px-4 py-2">Total</td>
          <td className="text-sm text-right px-4 py-2">
            {total_tokens.toLocaleString()}
          </td>
        </tr>
      </tbody>
    </table>
  );
}
