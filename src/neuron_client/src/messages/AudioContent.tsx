import { Download, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import AudioBarPlayer from "./AudioBarPlayer";

interface AudioContentProps {
  url: string;
  className?: string;
  preload?: string;
  showControls?: boolean;
  autoPlay?: boolean;
  onPlay?: () => void;
  onEnded?: () => void;
  onPause?: () => void;
}

const AudioContent: React.FC<AudioContentProps> = ({
  url,
  className,
  preload = "none",
  showControls = true,
  autoPlay = false,
  onPlay,
  onEnded,
  onPause,
}) => {
  const { toast } = useToast();

  return (
    <div className="flex gap-2">
      <AudioBarPlayer
        autoPlay={autoPlay}
        className={className}
        preload={preload}
        src={url}
        onEnded={onEnded}
        onPlay={onPlay}
        onPause={onPause}
      >
        {showControls && (
          <div className="flex flex-row gap-2">
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
                  <Copy className="h-4 w-4" />
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
                    <Download className="h-4 w-4" />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Download audio</TooltipContent>
            </Tooltip>
          </div>
        )}
      </AudioBarPlayer>
    </div>
  );
};

export default AudioContent;
