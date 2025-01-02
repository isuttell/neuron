import { Download, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import AudioPlayer from "./AudioPlayer";

interface AudioContentProps {
  url: string;
  className?: string;
  preload?: "none" | "metadata" | "auto";
}

const AudioContent: React.FC<AudioContentProps> = ({
  url,
  className,
  preload = "none",
}) => {
  const { toast } = useToast();

  return (
    <div className="flex gap-2">
      <AudioPlayer className={className} preload={preload} src={url} />
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
    </div>
  );
};

export default AudioContent;
