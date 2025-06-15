import { Images } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface MediaPanelToggleProps {
  isVisible: boolean;
  onChange: (visible: boolean) => void;
}

export default function MediaPanelToggle({
  isVisible,
  onChange,
}: MediaPanelToggleProps) {
  const toggleVisibility = () => {
    const newState = !isVisible;
    onChange(newState);
    localStorage.setItem("mediaPanelVisible", String(newState));
  };

  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <Button variant="ghost" size="icon" onClick={toggleVisibility}>
          <Images className="size-4" />
          <span className="sr-only">Toggle Media Panel</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">
{isVisible ? "Hide" : "Show"} Media
      </TooltipContent>
    </Tooltip>
  );
}
