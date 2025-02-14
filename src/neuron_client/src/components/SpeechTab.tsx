import { useAppSelector } from "@/hooks";
import { selectAllMedia } from "@/slices/mediaSlice";
import { useMemo, useRef, useState, useEffect } from "react";
import { MediaItem } from "@/types/media";
import { SpeechPlayer } from "./SpeechPlayer";
import ImageContent from "@/messages/ImageContent";
import VideoContent from "@/messages/VideoContent";
import { SubtitleContent } from "@/messages/SubtitleContent";
import SpeechAudioContent from "@/messages/SpeechAudioContent";
import { cn } from "@/lib/utils";

interface SpeechTabProps {
  threadId: string;
}

export function SpeechTab({ threadId }: SpeechTabProps) {
  const mediaItems = useAppSelector(selectAllMedia);
  const [currentIndex, setCurrentIndex] = useState<number>(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [shouldPlay, setShouldPlay] = useState(false);
  const [autoPlay, setAutoPlay] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const previousItemsLengthRef = useRef(0);
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  const isInitialLoadRef = useRef(true);

  const allItems = useMemo(
    () =>
      mediaItems
        .filter((item: MediaItem) => item.thread_id === threadId)
        .sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        ),
    [mediaItems, threadId]
  );

  const audioItems = useMemo(
    () =>
      allItems.filter(
        (item) => item.media_type === "audio" || item.media_type === "tts"
      ),
    [allItems]
  );

  // Create a mapping of item IDs to their audio indices
  const audioIndices = useMemo(() => {
    const indices = new Map<string, number>();
    allItems.forEach((item) => {
      if (item.media_type === "audio" || item.media_type === "tts") {
        const index = audioItems.findIndex((a) => a.id === item.id);
        if (index !== -1) {
          indices.set(item.id, index);
        }
      }
    });
    return indices;
  }, [allItems, audioItems]);

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

  // Handle new items and initial load
  useEffect(() => {
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      previousItemsLengthRef.current = audioItems.length;
      if (audioItems.length > 0) {
        setCurrentIndex(audioItems.length - 1); // Set to last item on initial load
      }
      return;
    }

    if (audioItems.length > previousItemsLengthRef.current) {
      const audio = audioRef.current;
      if (!audio) return;

      // If auto-play is enabled and nothing is playing, start with latest item
      if (autoPlay && !shouldPlay) {
        const newIndex = audioItems.length - 1;
        setCurrentIndex(newIndex);
        const item = audioItems[newIndex];
        const itemUrl = new URL(item.url, window.location.origin).href;
        audio.src = itemUrl;
        audio.play().catch(console.error);
        setShouldPlay(true);
      }
    }
    previousItemsLengthRef.current = audioItems.length;
  }, [audioItems, shouldPlay, autoPlay]);

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
    } else if (shouldPlay && audio.paused) {
      audio.play().catch(console.error);
    }
  }, [currentIndex, audioItems, shouldPlay]);

  // Unified scroll handling
  useEffect(() => {
    // Skip if no items or invalid index
    if (audioItems.length === 0 || currentIndex < 0) return;

    // Ensure refs array matches current items length
    if (itemRefs.current.length !== allItems.length) {
      itemRefs.current = new Array(allItems.length).fill(null);
    }

    // Find the actual index in allItems that corresponds to the current audio index
    const currentAudioItem = audioItems[currentIndex];
    const targetIndex = allItems.findIndex(
      (item) => item.id === currentAudioItem?.id
    );

    if (targetIndex === -1) return;

    // Use requestAnimationFrame for more reliable timing
    const scrollTimeout = requestAnimationFrame(() => {
      const targetRef = itemRefs.current[targetIndex];
      if (targetRef) {
        targetRef.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    });

    return () => cancelAnimationFrame(scrollTimeout);
  }, [audioItems, allItems, currentIndex]); // Dependencies cover both initial load and updates

  const handlePlay = (index?: number) => {
    setShouldPlay(true);
    if (!audioRef.current) return;

    const targetIndex = index ?? currentIndex;
    if (targetIndex >= 0 && targetIndex < audioItems.length) {
      const item = audioItems[targetIndex];
      const itemUrl = new URL(item.url, window.location.origin).href;
      if (audioRef.current.src !== itemUrl) {
        audioRef.current.src = itemUrl;
      }
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
      const itemUrl = new URL(item.url, window.location.origin).href;
      audioRef.current.src = itemUrl;
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
          {allItems.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">
              No media
            </div>
          ) : (
            <div className="space-y-2 pb-2">
              {allItems.map((item, index) => {
                const audioIndex = audioIndices.get(item.id) ?? -1;

                if (item.media_type === "audio") {
                  return (
                    <div
                      ref={(el) => (itemRefs.current[index] = el)}
                      key={item.id}
                    >
                      <SpeechAudioContent
                        url={item.url}
                        title={item.name}
                        description={item.description}
                        mediaItem={item}
                        isPlaying={isPlaying && currentIndex === audioIndex}
                        progress={
                          (currentIndex === audioIndex
                            ? currentTime / duration
                            : 0) * 100
                        }
                        onPlay={() => {
                          setCurrentIndex(audioIndex);
                          handlePlay(audioIndex);
                        }}
                        onPause={handlePause}
                        className={cn(
                          "rounded-md transition-colors border",
                          currentIndex === audioIndex && "bg-muted/25"
                        )}
                      />
                    </div>
                  );
                } else if (item.media_type === "tts") {
                  return (
                    <div
                      ref={(el) => (itemRefs.current[index] = el)}
                      key={item.id}
                    >
                      <SubtitleContent
                        item={item}
                        isPlaying={isPlaying && currentIndex === audioIndex}
                        onClick={() => {
                          setCurrentIndex(audioIndex);
                        }}
                        onPlayClick={() => {
                          setCurrentIndex(audioIndex);
                          handlePlay(audioIndex);
                        }}
                        onPauseClick={handlePause}
                        className={cn(
                          "rounded-md transition-colors border",
                          currentIndex === audioIndex && "bg-muted/25"
                        )}
                      />
                    </div>
                  );
                } else if (item.media_type === "image") {
                  return (
                    <ImageContent
                      key={item.id}
                      url={item.url}
                      alt={item.name}
                      description={item.description}
                      width={1024}
                      height={1024}
                      thumbnail_size="t"
                      showControls={false}
                      objectFit="contain"
                      mediaItem={item}
                    />
                  );
                } else if (item.media_type === "video") {
                  return (
                    <VideoContent
                      key={item.id}
                      url={item.url}
                      autoPlay={true}
                      controls={false}
                      loop={true}
                      showControls={false}
                      mediaItem={item}
                    />
                  );
                }
                return null;
              })}
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
          autoPlay={autoPlay}
          onAutoPlayChange={setAutoPlay}
        />
      )}
    </div>
  );
}
