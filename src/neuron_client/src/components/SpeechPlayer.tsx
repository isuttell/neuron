import { Button } from "@/components/ui/button";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";

interface SpeechPlayerProps {
  onPlay: () => void;
  onPause: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onGoToEnd: () => void;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  currentItem?: { name: string; description?: string } | null;
  canGoNext: boolean;
  canGoPrevious: boolean;
}

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

export function SpeechPlayer({
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
}: SpeechPlayerProps) {
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="border-t shadow-md bg-background flex-shrink-0 px-4 pt-6 scroll-smooth">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{formatTime(currentTime)}</span>
          <div
            className="flex-1 h-1 bg-muted rounded-full cursor-pointer relative group"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const x = e.clientX - rect.left;
              const percentage = x / rect.width;
              onSeek(percentage * duration);
            }}
          >
            <div
              className="absolute inset-y-0 left-0 bg-primary rounded-full transition-[width] duration-100"
              style={{ width: `${progress}%` }}
            />
            <div className="absolute inset-0 bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <span>{formatTime(duration)}</span>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={onPrevious}
              disabled={!canGoPrevious}
            >
              <SkipBack className="h-4 w-4" />
            </Button>

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

            <Button
              size="sm"
              variant="ghost"
              onClick={onNext}
              disabled={!canGoNext}
            >
              <SkipForward className="h-4 w-4" />
            </Button>

            <Button size="sm" variant="ghost" onClick={onGoToEnd}>
              <div className="flex">
                <SkipForward className="h-4 w-4" />
                <SkipForward className="h-4 w-4 -ml-2" />
              </div>
            </Button>
          </div>

          <div className="flex-1">
            <div className="text-sm font-medium">
              {currentItem ? (
                <>
                  <div>Now Playing</div>
                  <div className="text-muted-foreground">
                    {currentItem.name}
                  </div>
                </>
              ) : (
                <div>No track selected</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
