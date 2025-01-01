import { Bot } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ToggleSystemMessagesProps {
  showTools: boolean;
  onToggle: () => void;
}

export default function ToggleSystemMessages({
  showTools,
  onToggle,
}: ToggleSystemMessagesProps) {
  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <Button
          variant={showTools ? "default" : "ghost"}
          size="icon"
          onClick={onToggle}
        >
          <Bot className="size-4" />
          <span className="sr-only">Toggle System Messages</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">Toggle System Messages</TooltipContent>
    </Tooltip>
  );
}
