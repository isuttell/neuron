import { Download, Copy, Play, Pause, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useToast } from "@/hooks/use-toast";
import { AudioBarVisualization } from "@/components/AudioBarVisualization";
import { cn } from "@/lib/utils";
import { useEffect, useState, memo, useRef, useId } from "react";
import { useMediaPlayer } from "@/hooks/useMediaPlayer";
import { Spinner } from "@/components/ui/spinner";
import { MediaListDropdown } from "@/components/MediaListDropdown";
import { MediaItem } from "@/types/media";

interface AudioContentProps {
  url: string;
  title?: string;
  description?: string;
  className?: string;
  preload?: "" | "none" | "metadata" | "auto";
  autoPlay?: boolean;
  mediaItem?: MediaItem;
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

const AudioContent: React.FC<AudioContentProps> = memo(
  ({
    url,
    title,
    description,
    className,
    mediaItem,
    preload = "auto",
    autoPlay = false,
    onPlay,
    onEnded,
    onPause,
  }) => {
    const { toast } = useToast();
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [currentTime, setCurrentTime] = useState("0:00.00");
    const [duration, setDuration] = useState("0:00.00");
    const [isWaveDataLoading, setIsWaveDataLoading] = useState(true);
    const id = useId();
    const audioRef = useRef<HTMLAudioElement>();
    const { registerPlayer, unregisterPlayer, playPlayer, getOrCreateAudio } =
      useMediaPlayer();

    title = title || url.split("/").pop()?.split(".")[0] || "";

    useEffect(() => {
      const audio = (audioRef.current = getOrCreateAudio(url));
      audio.preload = preload || "auto";

      const handleTimeUpdate = () => {
        const newProgress = (audio.currentTime / audio.duration) * 100;
        setProgress(newProgress);
        setCurrentTime(formatTime(audio.currentTime));
      };

      const handleLoadedMetadata = () => {
        setDuration(formatTime(audio.duration));
      };

      const handleEnded = () => {
        setIsPlaying(false);
        setProgress(0);
        setCurrentTime("0:00.00");
        if (onEnded) onEnded();
      };

      const handlePlay = () => {
        if (audioRef.current?.paused) {
          setIsPlaying(false);
          return;
        }
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
        className={cn("flex rounded-lg flex-col w-full border", className)}
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
        <div className="text-sm text-gray-500 truncate p-2 border-t">
          {title}
        </div>
        <div className="flex flex-row gap-2 w-full border-t p-1 overflow-hidden">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button size="sm" variant="ghost" onClick={toggleAudio}>
                {isPlaying ? (
                  <Pause className="size-4" />
                ) : (
                  <Play className="size-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isPlaying ? "Pause" : "Play"}</TooltipContent>
          </Tooltip>
          {mediaItem && (
            <Tooltip>
              <TooltipTrigger>
                <MediaListDropdown size="sm" mediaItemId={mediaItem.id} />
              </TooltipTrigger>
              <TooltipContent>Add to list</TooltipContent>
            </Tooltip>
          )}

          <div className="flex-1" />
          {description && (
            <div className="flex items-center">
              <Popover>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <PopoverTrigger asChild>
                      <Button size="sm" variant="ghost">
                        <BookOpen className="size-4" />
                      </Button>
                    </PopoverTrigger>
                  </TooltipTrigger>
                  <TooltipContent>View description</TooltipContent>
                </Tooltip>
                <PopoverContent className="w-80">
                  <div className="text-sm whitespace-pre-wrap">
                    {description}
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.preventDefault();
                  navigator.clipboard.writeText(url);
                  toast({
                    title: "Audio URL copied to clipboard",
                  });
                }}
              >
                <Copy className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Copy audio URL</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                asChild
                onClick={(e) => {
                  e.stopPropagation();
                }}
              >
                <a
                  className="text-primary"
                  href={url}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Download className="size-4" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Download audio</TooltipContent>
          </Tooltip>
        </div>
      </div>
    );
  }
);

export default AudioContent;
