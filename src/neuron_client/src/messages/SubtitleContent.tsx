import { MediaItem } from "@/types/media";
import { cn } from "@/lib/utils";
import Content from "@/messages/Content";
import { Bot, Play, Pause, Copy, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";

interface SubtitleContentProps {
  item: MediaItem;
  isPlaying: boolean;
  onClick?: () => void;
  onPlayClick?: () => void;
  onPauseClick?: () => void;
  className?: string;
}

export function SubtitleContent({
  item,
  isPlaying,
  onClick,
  onPlayClick,
  onPauseClick,
  className,
}: SubtitleContentProps) {
  return (
    <div className={cn("cursor-pointer", className)} onClick={onClick}>
      <div className="p-3">
        <div className="flex items-center space-x-4">
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center min-w-[24px]">
                <Bot className="text-primary-foreground" size={14} />
              </div>
            </TooltipTrigger>
            <TooltipContent side="right">AI</TooltipContent>
          </Tooltip>
          <div className="flex flex-1 items-center justify-between">
            <div className="font-medium text-muted-foreground">{item.name}</div>
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
        </div>
        {item.description && (
          <div className="mt-4">
            <Content
              content={item.description}
              className="text-sm text-muted-foreground"
            />
          </div>
        )}
      </div>
      <div className="flex flex-row gap-2 w-full border-t p-1 overflow-hidden">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                if (isPlaying) {
                  onPauseClick?.();
                } else {
                  onPlayClick?.();
                }
              }}
            >
              {isPlaying ? (
                <Pause className="size-4" />
              ) : (
                <Play className="size-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isPlaying ? "Pause" : "Play"}</TooltipContent>
        </Tooltip>

        <div className="flex-1" />

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.preventDefault();
                navigator.clipboard.writeText(item.description || "");
                toast("Subtitle content copied to clipboard");
              }}
            >
              <Copy className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Copy subtitle content</TooltipContent>
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
                href={item.url}
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
