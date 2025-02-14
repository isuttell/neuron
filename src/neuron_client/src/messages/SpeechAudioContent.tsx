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
import { memo, useState } from "react";
import { Spinner } from "@/components/ui/spinner";
import { MediaListDropdown } from "@/components/MediaListDropdown";
import { MediaItem } from "@/types/media";

interface SpeechAudioContentProps {
  url: string;
  title?: string;
  description?: string;
  className?: string;
  isPlaying: boolean;
  progress: number;
  onPlay: () => void;
  mediaItem?: MediaItem;
}

const SpeechAudioContent: React.FC<SpeechAudioContentProps> = memo(
  ({
    url,
    title,
    description,
    className,
    isPlaying,
    progress,
    onPlay,
    mediaItem,
  }) => {
    const { toast } = useToast();
    const [isWaveDataLoading, setIsWaveDataLoading] = useState(true);

    title = title || url.split("/").pop()?.split(".")[0] || "";

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
          <AudioBarVisualization
            src={url}
            progress={progress}
            className={cn(
              "w-full rounded-md transition-opacity",
              isWaveDataLoading && "opacity-0"
            )}
            onSeek={() => {
              // Seek is handled by the parent SpeechPlayer
            }}
            onLoadingChange={setIsWaveDataLoading}
          />
        </div>
        <div className="text-sm text-gray-500 truncate p-2 border-t">
          {title}
        </div>
        <div className="flex flex-row gap-2 w-full border-t p-1 overflow-hidden">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button size="sm" variant="ghost" onClick={onPlay}>
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

export default SpeechAudioContent;
