import React, { useRef, useCallback } from "react";
import { useGlobalAudio } from "@/contexts/GlobalAudioContext";
import { Button } from "@/components/ui/button";
import { X, Pause, Play, SkipBack, SkipForward, Repeat } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AudioBarVisualization } from "./AudioBarVisualization";
import { useAppSelector, useAppDispatch } from "@/hooks";
import { getShowPlayer, togglePlayer } from "@/slices/audioSlice";
import { QueueSheet } from "./QueueSheet";

export function GlobalAudioPlayer() {
  const dispatch = useAppDispatch();
  const {
    currentUrl,
    toggleAudio,
    isPlaying,
    isLoading,
    error,
    progress,
    queue,
    skipNext,
    skipPrevious,
    currentTime,
    duration,
    seek,
    autoAdvance,
    toggleAutoAdvance,
  } = useGlobalAudio();

  const progressRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);

  const handleProgressClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = progressRef.current?.getBoundingClientRect();
      if (!rect) return;

      const x = e.clientX - rect.left;
      const percentage = (x / rect.width) * 100;
      seek(Math.max(0, Math.min(100, percentage)));
    },
    [seek]
  );

  const handleProgressMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      isDraggingRef.current = true;
      handleProgressClick(e);
    },
    [handleProgressClick]
  );

  const handleProgressMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDraggingRef.current) return;

      const rect = progressRef.current?.getBoundingClientRect();
      if (!rect) return;

      const x = e.clientX - rect.left;
      const percentage = (x / rect.width) * 100;
      seek(Math.max(0, Math.min(100, percentage)));
    },
    [seek]
  );

  const handleProgressMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  React.useEffect(() => {
    document.addEventListener("mousemove", handleProgressMouseMove);
    document.addEventListener("mouseup", handleProgressMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleProgressMouseMove);
      document.removeEventListener("mouseup", handleProgressMouseUp);
    };
  }, []);

  const show = useAppSelector(getShowPlayer);

  if (!show) return null;

  const currentTrackIndex = queue.findIndex((item) => item.url === currentUrl);
  const currentTrack = queue[currentTrackIndex];

  return (
    <div className="fixed w-[650px] top-2 right-2 m-4 bg-background border rounded-lg shadow-lg flex flex-col">
      {error && (
        <div className="px-4 py-2 text-sm text-destructive bg-destructive/10">
          {error}
        </div>
      )}
      <div className="h-[101px] border-b">
        {currentUrl && (
          <AudioBarVisualization
            key={currentUrl}
            src={currentUrl}
            progress={progress}
            className="w-full h-full"
            onSeek={seek}
          />
        )}
      </div>
      <div className="p-4 flex items-center gap-4">
        <div className="flex flex-col min-w-[200px] flex-1">
          <div className="text-sm font-medium">
            <div>Now Playing</div>
            {currentTrack?.title && (
              <div className="text-muted-foreground">{currentTrack.title}</div>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{currentTime}</span>
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
            <span>{duration}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                onClick={skipPrevious}
                disabled={queue.length <= 1 || currentTrackIndex === 0}
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
                onClick={toggleAudio}
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                ) : isPlaying ? (
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
                onClick={skipNext}
                disabled={
                  queue.length <= 1 || currentTrackIndex === queue.length - 1
                }
              >
                <SkipForward className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Next</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant={autoAdvance ? "default" : "ghost"}
                onClick={toggleAutoAdvance}
              >
                <Repeat className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {autoAdvance ? "Auto Advance On" : "Auto Advance Off"}
            </TooltipContent>
          </Tooltip>

          <QueueSheet />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => dispatch(togglePlayer())}
              >
                <X className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Hide Player</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
