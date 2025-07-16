import { cn } from "@/lib/utils";
import { Play, Pause, Maximize2 } from "lucide-react";
import { forwardRef, useState, useEffect, useRef, useId } from "react";
import { AudioBarVisualization } from "@/components/AudioBarVisualization";
import { useMediaPlayer } from "@/hooks/useMediaPlayer";
import { Button } from "@/components/ui/button";

interface AudioRendererProps {
  url: string;
  autoPlay?: boolean;
  controls?: boolean;
  loop?: boolean;
  muted?: boolean;
  preload?: "" | "none" | "metadata" | "auto";
  duration?: number;
  className?: string;
  isThumbnail?: boolean;
  title?: string;
  onExpand?: () => void;
}

export const AudioRenderer = forwardRef<HTMLAudioElement, AudioRendererProps>(
  (
    {
      url,
      autoPlay = false,
      controls = true,
      loop = false,
      muted = false,
      preload = "metadata",
      duration,
      className,
      isThumbnail = false,
      title,
      onExpand,
    },
    ref
  ) => {
    const [audioDuration, setAudioDuration] = useState<number | undefined>(duration);
    const [isWaveDataLoading, setIsWaveDataLoading] = useState(true);
    const [progress, setProgress] = useState(0);
    const [currentTime, setCurrentTime] = useState("0:00");
    const [isPlaying, setIsPlaying] = useState(false);
    const id = useId();
    const audioRef = useRef<HTMLAudioElement>();
    const { registerPlayer, unregisterPlayer, playPlayer, getOrCreateAudio } = useMediaPlayer();

    const formatTime = (seconds: number): string => {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
    };

    const displayTitle = title || url.split("/").pop()?.split(".")[0] || "Audio";

    useEffect(() => {
      if (!isThumbnail) return;

      const audio = (audioRef.current = getOrCreateAudio(url));
      audio.preload = preload || "metadata";

      // Initialize state from existing audio element
      const initializeState = () => {
        if (audio.duration && !isNaN(audio.duration)) {
          setAudioDuration(audio.duration);
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
        initializeState();
      };

      const handlePlay = () => {
        setIsPlaying(true);
      };

      const handlePause = () => {
        setIsPlaying(false);
      };

      const handleEnded = () => {
        setProgress(0);
        setCurrentTime("0:00");
        setIsPlaying(false);
      };

      audio.addEventListener("timeupdate", handleTimeUpdate);
      audio.addEventListener("loadedmetadata", handleLoadedMetadata);
      audio.addEventListener("play", handlePlay);
      audio.addEventListener("pause", handlePause);
      audio.addEventListener("ended", handleEnded);

      registerPlayer(id, url, audio);

      return () => {
        audio.removeEventListener("timeupdate", handleTimeUpdate);
        audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
        audio.removeEventListener("play", handlePlay);
        audio.removeEventListener("pause", handlePause);
        audio.removeEventListener("ended", handleEnded);
        unregisterPlayer(id, url);
      };
    }, [url, isThumbnail, preload, id, registerPlayer, unregisterPlayer, getOrCreateAudio]);

    const toggleAudio = async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
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
      }
    };

    const handleExpand = () => {
      // Let the event bubble up to DialogTrigger to open the dialog
      // Don't prevent default or stop propagation
      onExpand?.();
    };

    if (isThumbnail) {
      return (
        <div
          className={cn(
            "relative max-h-[120px] max-w-[400px] w-fit overflow-hidden rounded-lg border cursor-pointer hover:shadow-md transition-shadow",
            className
          )}
        >
          <div
            className="w-full relative flex justify-center items-center py-2"
            style={{
              aspectRatio: "4/1",
              backgroundColor: "#111111",
            }}
          >
            {currentTime !== "0:00" && (
              <div className="text-xs text-gray-400 absolute bottom-1 left-2">
                {currentTime}
              </div>
            )}
            <div className="text-xs text-gray-400 absolute bottom-1 right-2">
              {audioDuration ? formatTime(audioDuration) : "0:00"}
            </div>
            <AudioBarVisualization
              src={url}
              progress={progress}
              className={cn(
                "w-full rounded-md transition-opacity",
                isWaveDataLoading && "opacity-30"
              )}
              onLoadingChange={setIsWaveDataLoading}
            />
          </div>
          <div className="flex items-center justify-between p-2 border-t bg-background">
            <div className="text-sm text-gray-600 dark:text-gray-300 truncate">
              {displayTitle}
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
              {onExpand && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 w-6 hover:bg-accent hover:text-accent-foreground p-0"
                  onClick={handleExpand}
                >
                  <Maximize2 className="w-3 h-3" />
                </Button>
              )}
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className={cn("relative w-full", className)}>
        <audio
          ref={ref}
          className="w-full"
          src={url}
          autoPlay={autoPlay}
          muted={muted}
          controls={controls}
          loop={loop}
          preload={preload === "" ? "metadata" : preload}
          onLoadedMetadata={(e) => {
            const audio = e.target as HTMLAudioElement;
            setAudioDuration(audio.duration);
          }}
        >
          <source src={url} type="audio/mpeg" />
          <source src={url} type="audio/wav" />
          <source src={url} type="audio/ogg" />
          Your browser does not support the audio element.
        </audio>
      </div>
    );
  }
);

AudioRenderer.displayName = "AudioRenderer";
