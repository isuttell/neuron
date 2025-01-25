import React, { useRef, useCallback, useState, useEffect, useId } from "react";
import { Button } from "@/components/ui/button";
import {
  Pause,
  Play,
  SkipBack,
  SkipForward,
  ListVideo,
  Volume2,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { AudioBarVisualization } from "./AudioBarVisualization";
import { Spinner } from "./ui/spinner";
import { cn } from "@/lib/utils";
import { useMediaPlayer } from "@/contexts/MediaPlayerContext";

interface MediaItem {
  id: string;
  type: string;
  url: string;
  name: string;
}

interface MediaListAudioPlayerProps {
  mediaItems: MediaItem[];
}

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

export function MediaListAudioPlayer({
  mediaItems,
}: MediaListAudioPlayerProps) {
  const audioItems = mediaItems.filter((item) => item.type === "audio");
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState("0:00");
  const [duration, setDuration] = useState("0:00");
  const [autoAdvance, setAutoAdvance] = useState(true);
  const [autoPlayNew, setAutoPlayNew] = useState(false);
  const [isWaveDataLoading, setIsWaveDataLoading] = useState(false);
  const id = useId();
  const audioRef = useRef<HTMLAudioElement>(new Audio());
  const progressRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const previousItemsLengthRef = useRef(audioItems.length);
  const { registerPlayer, unregisterPlayer, playPlayer } = useMediaPlayer();

  const currentItem = currentIndex >= 0 ? audioItems[currentIndex] : null;

  const loadAndPlay = useCallback(
    (index: number) => {
      if (!audioRef.current || index < 0 || index >= audioItems.length) return;
      const item = audioItems[index];

      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsLoading(true);
      setError(null);
      setCurrentIndex(index);
      audioRef.current.src = item.url;
      audioRef.current.preload = "auto";

      playPlayer(id);
      const playPromise = audioRef.current.play();
      if (playPromise) {
        playPromise
          .then(() => {
            setIsLoading(false);
          })
          .catch((err) => {
            console.error("Failed to play audio:", err);
            setError("Audio playback requires user interaction");
            setIsLoading(false);
          });
      }
    },
    [audioItems, id, playPlayer]
  );

  const toggleAudio = useCallback(() => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      if (currentIndex === -1 && audioItems.length > 0) {
        loadAndPlay(0);
      } else {
        playPlayer(id);
        audioRef.current.play().catch((err) => {
          setError(err.message);
        });
      }
    }
  }, [isPlaying, currentIndex, audioItems, loadAndPlay, id, playPlayer]);

  const skipNext = useCallback(() => {
    if (currentIndex >= audioItems.length - 1) return;
    loadAndPlay(currentIndex + 1);
  }, [currentIndex, audioItems, loadAndPlay]);

  const skipPrevious = useCallback(() => {
    if (currentIndex <= 0) return;
    loadAndPlay(currentIndex - 1);
  }, [currentIndex, loadAndPlay]);

  const handleProgressClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = progressRef.current?.getBoundingClientRect();
      if (!rect || !audioRef.current) return;

      const x = e.clientX - rect.left;
      const percentage = (x / rect.width) * 100;
      const time = (percentage / 100) * audioRef.current.duration;
      audioRef.current.currentTime = time;
      setProgress(percentage);
    },
    []
  );

  const handleProgressMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      isDraggingRef.current = true;
      handleProgressClick(e);
    },
    [handleProgressClick]
  );

  const handleProgressMouseMove = useCallback((e: MouseEvent) => {
    if (!isDraggingRef.current || !audioRef.current) return;

    const rect = progressRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const percentage = (x / rect.width) * 100;
    const time = (percentage / 100) * audioRef.current.duration;
    audioRef.current.currentTime = time;
    setProgress(percentage);
  }, []);

  const handleProgressMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  // Handle auto-play for new items
  useEffect(() => {
    if (autoPlayNew && audioItems.length > previousItemsLengthRef.current) {
      const newItemIndex = audioItems.length - 1;
      loadAndPlay(newItemIndex);
    }
    previousItemsLengthRef.current = audioItems.length;
  }, [audioItems.length, autoPlayNew, loadAndPlay]);

  useEffect(() => {
    const audio = audioRef.current;

    const handleTimeUpdate = () => {
      if (!audio) return;
      const newProgress = (audio.currentTime / audio.duration) * 100;
      const newCurrentTime = formatTime(audio.currentTime);
      setProgress(newProgress);
      setCurrentTime(newCurrentTime);
    };

    const handleLoadedMetadata = () => {
      if (audio) {
        setDuration(formatTime(audio.duration));
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      if (autoAdvance && currentIndex < audioItems.length - 1) {
        loadAndPlay(currentIndex + 1);
      }
    };

    registerPlayer(id, audio);

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("play", () => setIsPlaying(true));
    audio.addEventListener("pause", () => setIsPlaying(false));

    document.addEventListener("mousemove", handleProgressMouseMove);
    document.addEventListener("mouseup", handleProgressMouseUp);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("play", () => setIsPlaying(true));
      audio.removeEventListener("pause", () => setIsPlaying(false));
      document.removeEventListener("mousemove", handleProgressMouseMove);
      document.removeEventListener("mouseup", handleProgressMouseUp);
      unregisterPlayer(id);
    };
  }, [
    handleProgressMouseMove,
    handleProgressMouseUp,
    autoAdvance,
    currentIndex,
    audioItems.length,
    loadAndPlay,
    id,
    registerPlayer,
    unregisterPlayer,
  ]);

  if (audioItems.length === 0) return null;

  return (
    <div className="border-t">
      {error && (
        <div className="px-4 py-2 text-sm text-destructive bg-destructive/10">
          {error}
        </div>
      )}
      <div
        className="h-[101px] border-b relative"
        style={{ backgroundColor: "#111111" }}
      >
        {isWaveDataLoading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <Spinner size={48} />
          </div>
        )}
        {currentItem && (
          <AudioBarVisualization
            key={currentItem.url}
            src={currentItem.url}
            progress={progress}
            className={cn(
              "w-full h-full transition-opacity",
              isWaveDataLoading && "opacity-0"
            )}
            onSeek={(percentage) => {
              if (!audioRef.current) return;
              const time = (percentage / 100) * audioRef.current.duration;
              audioRef.current.currentTime = time;
              setProgress(percentage);
            }}
            onLoadingChange={setIsWaveDataLoading}
          />
        )}
      </div>
      <div className="p-4 flex items-center gap-4">
        <div className="flex flex-col min-w-[200px] flex-1">
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
                disabled={currentIndex <= 0}
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
                disabled={currentIndex >= audioItems.length - 1}
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
                onClick={() => setAutoAdvance(!autoAdvance)}
              >
                <ListVideo className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {autoAdvance ? "Auto Advance On" : "Auto Advance Off"}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant={autoPlayNew ? "default" : "ghost"}
                onClick={() => setAutoPlayNew(!autoPlayNew)}
              >
                <Volume2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {autoPlayNew
                ? "Auto-play New Items On"
                : "Auto-play New Items Off"}
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
