import { Music2 } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppDispatch } from "@/hooks";
import { togglePlayer } from "@/slices/audioSlice";

export default function TogglePlayerButton() {
  const dispatch = useAppDispatch();

  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => dispatch(togglePlayer())}
          className="size-10"
        >
          <Music2 className="size-4" />
          <span className="sr-only">Toggle Audio Player</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">Toggle Audio Player</TooltipContent>
    </Tooltip>
  );
}
