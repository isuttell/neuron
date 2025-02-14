import { MediaItem } from "@/types/media";
import { cn } from "@/lib/utils";
import Content from "@/messages/Content";
import { Bot } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";

interface SubtitleContentProps {
  item: MediaItem;
  isCurrentItem: boolean;
  isPlaying: boolean;
  onClick?: () => void;
}

export function SubtitleContent({
  item,
  isCurrentItem,
  isPlaying,
  onClick,
}: SubtitleContentProps) {
  return (
    <div
      className={cn(
        "p-3 rounded-md hover:bg-muted/50 transition-colors cursor-pointer border",
        isCurrentItem && !isPlaying && "border-primary",
        isCurrentItem && isPlaying && "bg-muted"
      )}
      onClick={onClick}
    >
      <div className="flex items-center space-x-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center min-w-[24px]">
              <Bot className="text-primary-foreground" size={14} />
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">AI</TooltipContent>
        </Tooltip>
        <div className="flex flex-1 items-center justify-between">
          <div className="font-medium">{item.name}</div>
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
        <div className="mt-1">
          <Content
            content={item.description}
            className="text-sm text-muted-foreground"
          />
        </div>
      )}
    </div>
  );
}
