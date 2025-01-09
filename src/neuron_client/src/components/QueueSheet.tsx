import { useGlobalAudio } from "@/contexts/GlobalAudioContext";
import { Button } from "@/components/ui/button";
import { Volume2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { List } from "lucide-react";
import { cn } from "@/lib/utils";

export function QueueSheet() {
  const { queue, currentUrl, isPlaying, playAudio, clearQueue } =
    useGlobalAudio();

  return (
    <Sheet>
      <Tooltip>
        <TooltipTrigger asChild>
          <SheetTrigger asChild>
            <Button size="sm" variant="ghost">
              <List className="h-4 w-4" />
            </Button>
          </SheetTrigger>
        </TooltipTrigger>
        <TooltipContent>Queue</TooltipContent>
      </Tooltip>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Queue</SheetTitle>
        </SheetHeader>
        <div className="mt-4">
          {queue.map((item, index) => (
            <div
              key={item.key}
              className={cn(
                "flex items-center gap-2 p-2 rounded-md cursor-pointer",
                "hover:bg-accent/50 transition-colors",
                item.url === currentUrl && "bg-primary/10 text-primary"
              )}
              onClick={() => {
                playAudio(item.url, item.title);
              }}
            >
              <div className="flex items-center gap-2 flex-1">
                {item.url === currentUrl && isPlaying && (
                  <Volume2 className="h-4 w-4 animate-pulse" />
                )}
                <span className="text-sm">
                  {index + 1}. {item.title || "Untitled"}
                </span>
              </div>
              {item.url === currentUrl && (
                <span className="text-xs text-muted-foreground">
                  {isPlaying ? "Playing" : "Paused"}
                </span>
              )}
            </div>
          ))}
          {queue.length === 0 && (
            <div className="text-center text-muted-foreground">
              Queue is empty
            </div>
          )}
        </div>
        {queue.length > 0 && (
          <Button
            className="mt-4 w-full"
            variant="destructive"
            onClick={() => clearQueue()}
          >
            Clear Queue
          </Button>
        )}
      </SheetContent>
    </Sheet>
  );
}
