import { PanelRight } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export type WidthMode = "hidden" | "narrow" | "wide";
const widthModeOrder: WidthMode[] = ["hidden", "narrow", "wide"];

interface MediaPanelWidthProps {
  widthMode: WidthMode;
  onChange: (mode: WidthMode) => void;
}

export default function MediaPanelWidth({
  widthMode,
  onChange,
}: MediaPanelWidthProps) {
  const cycleWidthMode = () => {
    const newWidthMode = widthModeOrder[
      (widthModeOrder.indexOf(widthMode) + 1) % widthModeOrder.length
    ] as WidthMode;
    onChange(newWidthMode);
    localStorage.setItem("widthMode", newWidthMode);
  };

  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <Button variant="ghost" size="icon" onClick={cycleWidthMode}>
          <PanelRight className="size-6" />
          <span className="sr-only">Toggle Width Mode</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">Change Media Panel Width</TooltipContent>
    </Tooltip>
  );
}
