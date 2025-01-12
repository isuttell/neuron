import { Music2, Play } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppDispatch } from "@/hooks";
import { togglePlayer } from "@/slices/audioSlice";
import { useGlobalAudio } from "@/contexts/GlobalAudioContext";

export default function TogglePlayerButton() {
  const dispatch = useAppDispatch();
  const { isPlaying, autoAdvance } = useGlobalAudio();
  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <Button
          variant={autoAdvance ? "outline" : "ghost"}
          size="icon"
          onClick={() => dispatch(togglePlayer())}
          className="size-10"
        >
          {isPlaying ? (
            <Play className="size-4" />
          ) : (
            <Music2 className="size-4" />
          )}
          <span className="sr-only">Toggle Audio Player</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">Toggle Audio Player</TooltipContent>
    </Tooltip>
  );
}
