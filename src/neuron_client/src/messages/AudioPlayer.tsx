import { Play, Pause } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AudioBarVisualization } from "@/components/AudioBarVisualization";
import { cn } from "@/lib/utils";
import React, { useEffect, useState, memo, useRef, useId } from "react";
import { useMediaPlayer } from "@/hooks/useMediaPlayer";
import { Spinner } from "@/components/ui/spinner";

interface AudioPlayerProps {
  url: string;
  title?: string;
  className?: string;
  preload?: "" | "none" | "metadata" | "auto";
  autoPlay?: boolean;
  duration?: number;
  onPlay?: () => void;
  onEnded?: () => void;
  onPause?: () => void;
}

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  const fraction = seconds % 1;
  return `${minutes}:${remainingSeconds
    .toString()
    .padStart(2, "0")}.${Math.floor(fraction * 100)
    .toString()
    .padStart(2, "0")}`;
};

const AudioPlayer: React.FC<AudioPlayerProps> = memo(
  ({
    url,
    title,
    className,
    duration: propDuration,
    preload = "auto",
    autoPlay = false,
    onPlay,
    onEnded,
    onPause,
  }) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [currentTime, setCurrentTime] = useState("0:00.00");
    const [duration, setDuration] = useState(propDuration ? formatTime(propDuration) : "0:00.00");
    const [isWaveDataLoading, setIsWaveDataLoading] = useState(true);
    const id = useId();
    const audioRef = useRef<HTMLAudioElement>();
    const { registerPlayer, unregisterPlayer, playPlayer, getOrCreateAudio } =
      useMediaPlayer();

    title = title || url.split("/").pop()?.split(".")[0] || "";

    useEffect(() => {
      const audio = (audioRef.current = getOrCreateAudio(url));
      audio.preload = preload || "auto";

      // Initialize state from existing audio element
      const initializeState = () => {
        if (audio.duration && !isNaN(audio.duration)) {
          setDuration(formatTime(audio.duration));
          const newProgress = (audio.currentTime / audio.duration) * 100;
          setProgress(newProgress);
          setCurrentTime(formatTime(audio.currentTime));
        }
        setIsPlaying(!audio.paused);
      };

      // Initialize immediately if metadata is already loaded
      if (audio.readyState >= 1) {
        initializeState();
      }

      const handleTimeUpdate = () => {
        const newProgress = (audio.currentTime / audio.duration) * 100;
        setProgress(newProgress);
        setCurrentTime(formatTime(audio.currentTime));
      };

      const handleLoadedMetadata = () => {
        setDuration(formatTime(audio.duration));
        initializeState();
      };

      const handleEnded = () => {
        setIsPlaying(false);
        setProgress(0);
        setCurrentTime("0:00.00");
        if (onEnded) onEnded();
      };

      const handlePlay = () => {
        setIsPlaying(true);
        if (onPlay) onPlay();
      };

      const handlePause = () => {
        setIsPlaying(false);
        if (onPause) onPause();
      };

      audio.addEventListener("timeupdate", handleTimeUpdate);
      audio.addEventListener("loadedmetadata", handleLoadedMetadata);
      audio.addEventListener("ended", handleEnded);
      audio.addEventListener("play", handlePlay);
      audio.addEventListener("pause", handlePause);

      registerPlayer(id, url, audio);

      if (autoPlay) {
        audio.play().catch(console.error);
      }

      return () => {
        audio.removeEventListener("timeupdate", handleTimeUpdate);
        audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
        audio.removeEventListener("ended", handleEnded);
        audio.removeEventListener("play", handlePlay);
        audio.removeEventListener("pause", handlePause);
        unregisterPlayer(id, url);
      };
    }, [
      url,
      autoPlay,
      onPlay,
      onPause,
      onEnded,
      id,
      registerPlayer,
      unregisterPlayer,
      getOrCreateAudio,
      preload,
    ]);

    const toggleAudio = async () => {
      if (!audioRef.current) return;
      try {
        if (audioRef.current.paused) {
          playPlayer(id);
          await audioRef.current.play();
        } else {
          audioRef.current.pause();
        }
      } catch (error) {
        console.error(error);
        setIsPlaying(false);
      }
    };

    const handleSeek = (percentage: number) => {
      if (!audioRef.current) return;
      const time = (percentage / 100) * audioRef.current.duration;
      audioRef.current.currentTime = time;
      setProgress(percentage);
    };

    return (
      <div
        className={cn("flex rounded-lg flex-col w-full min-w-0 max-w-full sm:max-w-[400px] md:max-w-[500px] border", className)}
        data-audio-url={url}
      >
        <div
          className="w-full relative flex justify-center items-center py-3"
          style={{
            aspectRatio: "5/1",
            backgroundColor: "#111111",
          }}
        >
          {isWaveDataLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <Spinner size={32} />
            </div>
          )}
          {currentTime !== "0:00.00" && (
            <div className="text-xs text-gray-500 truncate p-1 absolute bottom-0 left-0">
              {currentTime}
            </div>
          )}
          <div className="text-xs text-gray-500 truncate p-1 absolute bottom-0 right-0">
            {duration}
          </div>
          <AudioBarVisualization
            src={url}
            progress={progress}
            className={cn(
              "w-full rounded-md transition-opacity",
              isWaveDataLoading && "opacity-0"
            )}
            onSeek={handleSeek}
            onLoadingChange={setIsWaveDataLoading}
          />
        </div>
        <div className="flex items-center justify-between p-2 border-t bg-background">
          <div className="text-sm text-gray-500 truncate">
            {title}
          </div>
          <div className="flex items-center gap-1 ml-2">
            <Button
              size="sm"
              variant="ghost"
              className="h-6 w-6 hover:bg-accent hover:text-accent-foreground p-0"
              onClick={toggleAudio}
            >
              {isPlaying ? (
                <Pause className="w-3 h-3" />
              ) : (
                <Play className="w-3 h-3" />
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  }
);

export default AudioPlayer;
