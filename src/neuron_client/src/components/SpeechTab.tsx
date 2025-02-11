import { useAppSelector } from "@/hooks";
import { selectAllMedia } from "@/slices/mediaSlice";
import { useMemo, useRef, useState, useEffect } from "react";
import { MediaItem } from "@/types/media";
import { SpeechPlayer } from "./SpeechPlayer";
import { cn } from "@/lib/utils";
import Content from "@/messages/Content";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import FuzzyTimeAgo from "./FuzzyTimeAgo";

interface SpeechTabProps {
  threadId: string;
}

export function SpeechTab({ threadId }: SpeechTabProps) {
  const mediaItems = useAppSelector(selectAllMedia);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [shouldPlay, setShouldPlay] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const previousItemsLengthRef = useRef(0);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  const isInitialLoadRef = useRef(true);

  const audioItems = useMemo(
    () =>
      mediaItems
        .filter(
          (item: MediaItem) =>
            item.thread_id === threadId && item.media_type === "audio"
        )
        .sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        ),
    [mediaItems, threadId]
  );

  // Initialize audio element
  useEffect(() => {
    const audio = new Audio();
    audio.preload = "auto";
    audioRef.current = audio;

    return () => {
      if (audio) {
        audio.pause();
        audio.src = "";
        audioRef.current = null;
      }
    };
  }, []); // Only on mount/unmount

  // Reset state when threadId changes
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.src = "";
    }

    setCurrentIndex(-1);
    setIsPlaying(false);
    setShouldPlay(false);
    setCurrentTime(0);
    setDuration(0);
    previousItemsLengthRef.current = 0;
    isInitialLoadRef.current = true;
    itemRefs.current = [];
  }, [threadId]);

  // Set up audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };
    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };
    const handleEnded = () => {
      // Move to next item if available
      if (currentIndex < audioItems.length - 1) {
        setCurrentIndex(currentIndex + 1);
        // shouldPlay state will trigger playback in source change
      } else {
        setShouldPlay(false); // Only clear intent at end of queue
      }
    };
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = (e: ErrorEvent) => {
      console.error("Audio error:", e);
      setIsPlaying(false);
    };

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("error", handleError);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("error", handleError);
    };
  }, [audioItems.length, currentIndex]);

  // Handle new items
  useEffect(() => {
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      previousItemsLengthRef.current = audioItems.length;
      return;
    }

    if (audioItems.length > previousItemsLengthRef.current) {
      const audio = audioRef.current;
      if (!audio) return;

      // If nothing is playing, start with latest item
      if (!shouldPlay) {
        const newIndex = audioItems.length - 1;
        setCurrentIndex(newIndex);
        const item = audioItems[newIndex];
        audio.src = item.url;
        audio.play().catch(console.error);
        setShouldPlay(true);
      }
    }
    previousItemsLengthRef.current = audioItems.length;
  }, [audioItems, shouldPlay]);

  // Handle source changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || currentIndex < 0 || currentIndex >= audioItems.length) return;

    const item = audioItems[currentIndex];
    const itemUrl = new URL(item.url, window.location.origin).href;
    if (audio.src !== itemUrl) {
      audio.src = itemUrl;
      if (shouldPlay) {
        audio.play().catch(console.error);
      }
    }
  }, [currentIndex, audioItems, shouldPlay]);

  // Initial scroll on mount
  useEffect(() => {
    // Wait for items to be available and current index to be set
    if (audioItems.length > 0 && currentIndex >= 0) {
      setTimeout(() => {
        itemRefs.current[currentIndex]?.scrollIntoView({
          behavior: "smooth",
          block: "center", // Center the item in view
        });
      }, 300); // Longer delay to ensure render
    }
  }, [audioItems.length, currentIndex]); // Include both deps

  const handlePlay = () => {
    setShouldPlay(true);
    if (!audioRef.current) return;

    if (currentIndex === -1 && audioItems.length > 0) {
      setCurrentIndex(0);
      const item = audioItems[0];
      audioRef.current.src = item.url;
      audioRef.current.play().catch(console.error);
    } else {
      audioRef.current.play().catch(console.error);
    }
  };

  const handlePause = () => {
    setShouldPlay(false);
    if (audioRef.current) {
      audioRef.current.pause();
    }
  };

  const handleNext = () => {
    if (currentIndex < audioItems.length - 1) {
      setCurrentIndex(currentIndex + 1);
      if (shouldPlay) {
        audioRef.current?.play().catch(console.error);
      }
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      if (shouldPlay) {
        audioRef.current?.play().catch(console.error);
      }
    }
  };

  const handleGoToEnd = () => {
    const newIndex = audioItems.length - 1;
    setCurrentIndex(newIndex);
    // Don't auto-play, just prepare for next item
    if (audioRef.current) {
      const item = audioItems[newIndex];
      audioRef.current.src = item.url;
    }
  };

  const handleSeek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto mb-2">
        <div className="space-y-2 ">
          {audioItems.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">
              No audio
            </div>
          ) : (
            <div className="space-y-2 pb-2">
              {audioItems.map((item, index) => (
                <div
                  ref={(el) => (itemRefs.current[index] = el)}
                  key={item.id}
                  className={cn(
                    "p-3 rounded-md hover:bg-muted/50 transition-colors cursor-pointer border",
                    index === currentIndex && !isPlaying && "border-primary",
                    index === currentIndex && isPlaying && "bg-muted"
                  )}
                  onClick={() => setCurrentIndex(index)}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium">{item.name}</div>
                    {item.created_at && (
                      <Tooltip delayDuration={0}>
                        <TooltipTrigger>
                          <FuzzyTimeAgo
                            className="text-xs text-gray-500"
                            timestamp={item.created_at}
                          />
                        </TooltipTrigger>
                        <TooltipContent side="bottom">
                          <span className="p-4">
                            {new Date(item.created_at).toLocaleString()}
                          </span>
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </div>
                  {item.description && (
                    <div className="mt-1">
                      <Content
                        content={item.description}
                        className="text-sm text-muted-foreground"
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {audioItems.length > 0 && (
        <SpeechPlayer
          onPlay={handlePlay}
          onPause={handlePause}
          onNext={handleNext}
          onPrevious={handlePrevious}
          onGoToEnd={handleGoToEnd}
          isPlaying={isPlaying}
          currentTime={currentTime}
          duration={duration}
          onSeek={handleSeek}
          currentItem={currentIndex >= 0 ? audioItems[currentIndex] : null}
          canGoNext={currentIndex < audioItems.length - 1}
          canGoPrevious={currentIndex > 0}
        />
      )}
    </div>
  );
}
