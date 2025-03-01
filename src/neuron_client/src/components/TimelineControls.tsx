import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import {
  ListVideo,
  MonitorPause,
  Pause,
  Play,
  SkipBack,
  SkipForward,
} from "lucide-react";
import { AudioBarVisualization } from "./AudioBarVisualization";
import { Spinner } from "./ui/spinner";

import React, { useRef, useState } from "react";

interface TimelineControlsProps {
  className?: string;
  onPlay: () => void;
  onPause: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onGoToEnd: () => void;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  currentItem?: {
    name: string;
    description?: string;
    url: string;
  } | null;
  canGoNext: boolean;
  canGoPrevious: boolean;
  autoPlay: boolean;
  onAutoPlayChange: (enabled: boolean) => void;
}

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

export function TimelineControls({
  className,
  onPlay,
  onPause,
  onNext,
  onPrevious,
  onGoToEnd,
  isPlaying,
  currentTime,
  duration,
  onSeek,
  currentItem,
  canGoNext,
  canGoPrevious,
  autoPlay,
  onAutoPlayChange,
}: TimelineControlsProps) {
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const progressRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const [isWaveDataLoading, setIsWaveDataLoading] = useState(false);

  const handleProgressMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    isDraggingRef.current = true;
    const rect = progressRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    onSeek(percentage * duration);
  };

  React.useEffect(() => {
    const handleProgressMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current || !progressRef.current) return;
      const rect = progressRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
      const percentage = x / rect.width;
      onSeek(percentage * duration);
    };

    const handleProgressMouseUp = () => {
      isDraggingRef.current = false;
    };
    document.addEventListener("mousemove", handleProgressMouseMove);
    document.addEventListener("mouseup", handleProgressMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleProgressMouseMove);
      document.removeEventListener("mouseup", handleProgressMouseUp);
    };
  }, [duration, onSeek]);

  return (
    <div
      className={cn(
        "shadow-md bg-background flex-shrink-0 scroll-smooth",
        className
      )}
    >
      <div
        className="h-[101px] relative border rounded-lg my-2"
        style={{ backgroundColor: "#111111" }}
      >
        {currentItem && (
          <>
            {isWaveDataLoading && (
              <div className="absolute inset-0 flex items-center justify-center z-10">
                <Spinner size={48} />
              </div>
            )}
            <AudioBarVisualization
              key={currentItem.url}
              src={currentItem.url}
              progress={progress}
              onSeek={(percentage) => onSeek((percentage * duration) / 100)}
              className={cn(
                "w-full h-full transition-opacity",
                isWaveDataLoading && "opacity-0"
              )}
              onLoadingChange={setIsWaveDataLoading}
            />
          </>
        )}
      </div>
      <div className="flex flex-col gap-4 px-4 py-2">
        <div className="flex items-center mb-2">
          <div className="text-sm font-medium">
            {currentItem ? (
              <>
                <div>Now Playing</div>
                <div className="text-muted-foreground">{currentItem.name}</div>
              </>
            ) : (
              <div>No track selected</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
          <span>{formatTime(currentTime)}</span>
          <div
            ref={progressRef}
            className="flex-1 h-1 bg-muted rounded-full cursor-pointer relative group"
            onMouseDown={handleProgressMouseDown}
          >
            <div
              className="absolute inset-y-0 left-0 bg-primary rounded-full transition-[width] duration-75"
              style={{ width: `${progress}%` }}
            />
            <div className="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-3 w-3 rounded-full bg-primary opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ left: `${progress}%` }}
            />
          </div>
          <span>{formatTime(duration)}</span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onPrevious}
                  disabled={!canGoPrevious}
                >
                  <SkipBack className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Previous</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={isPlaying ? onPause : onPlay}
                >
                  {isPlaying ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{isPlaying ? "Pause" : "Play"}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onNext}
                  disabled={!canGoNext}
                >
                  <SkipForward className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Next</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="sm" variant="ghost" onClick={onGoToEnd}>
                  <div className="flex">
                    <SkipForward className="h-4 w-4" />
                    <SkipForward className="h-4 w-4 -ml-2" />
                  </div>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Go to End</TooltipContent>
            </Tooltip>
          </div>

          {currentItem && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  variant={"ghost"}
                  onClick={() => onAutoPlayChange(!autoPlay)}
                >
                  {autoPlay ? (
                    <MonitorPause className="h-4 w-4" />
                  ) : (
                    <ListVideo className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {autoPlay ? "Disable auto-play" : "Enable auto-play audio"}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  );
}
