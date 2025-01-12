import { Download, Copy, Play, Pause, Plus } from "lucide-react";
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
import { useEffect } from "react";

interface AudioContentProps {
  url: string;
  className?: string;
  preload?: string;
  autoPlay?: boolean;
  onPlay?: () => void;
  onEnded?: () => void;
  onPause?: () => void;
}

const AudioContent: React.FC<AudioContentProps> = ({ url, className }) => {
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
  const title = url.split("/").pop()?.split(".")[0] || "";
  const isActive = currentUrl === url;

  useEffect(() => {
    addToQueue(url, title);
  }, [url]);

  return (
    <div
      className={cn("flex rounded-lg flex-col w-full", className)}
      style={{
        aspectRatio: "3/1",
        backgroundColor: "#111111",
      }}
    >
      <div className="w-full relative">
        <AudioBarVisualization
          src={url}
          progress={isActive ? progress : 0}
          className="w-full rounded-md"
          onSeek={isActive ? seek : undefined}
        />

        <div className="flex flex-row gap-2 w-full justify-end absolute bottom-2 right-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
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
                variant="outline"
                onClick={() => playAudio(url, title, false)}
              >
                <Plus className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Add to Queue</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                variant="outline"
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
                variant="outline"
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
      <div
        className="text-sm text-gray-500 truncate p-2 pt-0"
        style={{
          backgroundColor: "#111111",
        }}
      >
        {title}
      </div>
    </div>
  );
};

export default AudioContent;
