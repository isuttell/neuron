import { Download, Copy, Play, Pause, Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { AudioBarVisualization } from "@/components/AudioBarVisualization";
import { cn } from "@/lib/utils";
import { useGlobalAudio } from "@/contexts/GlobalAudioContext";
import { useEffect, useState } from "react";
import { Spinner } from "@/components/ui/spinner";

interface AudioContentProps {
  url: string;
  title?: string;
  className?: string;
  preload?: string;
  autoPlay?: boolean;
  onPlay?: () => void;
  onEnded?: () => void;
  onPause?: () => void;
}

const AudioContent: React.FC<AudioContentProps> = ({
  url,
  title,
  className,
}) => {
  const { toast } = useToast();
  const {
    playAudio,
    currentUrl,
    isPlaying,
    progress,
    seek,
    toggleAudio,
    addToQueue,
  } = useGlobalAudio();
  title = title || url.split("/").pop()?.split(".")[0] || "";
  const isActive = currentUrl === url;
  const [isWaveDataLoading, setIsWaveDataLoading] = useState(true);

  useEffect(() => {
    addToQueue(url, title);
  }, [url]);

  return (
    <div className={cn("flex rounded-lg flex-col w-full border", className)}>
      <div
        className="w-full relative flex justify-center items-center"
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
        <AudioBarVisualization
          src={url}
          progress={isActive ? progress : 0}
          className={cn(
            "w-full rounded-md transition-opacity",
            isWaveDataLoading && "opacity-0"
          )}
          onSeek={isActive ? seek : undefined}
          onLoadingChange={setIsWaveDataLoading}
        />
      </div>
      <div className="text-sm text-gray-500 truncate p-2 border-t">{title}</div>
      <div className="flex flex-row gap-2 w-full border-t p-1 overflow-hidden">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                if (currentUrl === url && isPlaying) {
                  toggleAudio();
                } else {
                  playAudio(url, title, true);
                }
              }}
            >
              {currentUrl === url && isPlaying ? (
                <Pause className="size-4" />
              ) : (
                <Play className="size-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            {currentUrl === url && isPlaying ? "Pause" : "Play Now"}
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => playAudio(url, title, false)}
            >
              <Plus className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Add to Queue</TooltipContent>
        </Tooltip>
        <div className="flex-1" />
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
};

export default AudioContent;
