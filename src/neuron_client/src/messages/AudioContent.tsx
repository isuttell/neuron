import MediaDialogComponent from "@/components/MediaDialog";
import { AudioRenderer } from "@/components/media/AudioRenderer";
import { MediaActions } from "@/components/media/MediaActions";
import { cn } from "@/lib/utils";
import { MediaItem } from "@/types/media";
import AudioPlayer from "./AudioPlayer";
import { Button } from "@/components/ui/button";
import { Copy } from "lucide-react";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface AudioContentProps {
  className?: string;
  url: string;
  title?: string;
  description?: string;
  duration?: number;
  autoPlay?: boolean;
  loop?: boolean;
  muted?: boolean;
  controls?: boolean;
  preload?: "" | "none" | "metadata" | "auto";
  showControls?: boolean;
  mediaItem?: MediaItem;
  metadata?: Record<string, unknown>;
  onPlay?: () => void;
  onEnded?: () => void;
  onPause?: () => void;
}

const AudioContent: React.FC<AudioContentProps> = ({
  url,
  title,
  description,
  duration,
  autoPlay = false,
  loop = false,
  muted = false,
  preload = "metadata",
  className,
  showControls = false,
  mediaItem,
  metadata,
  onPlay,
  onEnded,
  onPause,
}) => {
  const handleExpand = () => {
    // Let the event bubble up to trigger the dialog
    // The AudioRenderer is inside the DialogTrigger, so this will open the dialog
  };

  const trigger = (
    <div
      className={cn(
        "relative w-fit overflow-hidden",
        className
      )}
    >
      <AudioRenderer
        url={url}
        title={title}
        duration={duration}
        autoPlay={false}
        controls={false}
        loop={loop}
        muted={muted}
        preload={preload}
        isThumbnail={true}
        onExpand={handleExpand}
      />
      {showControls && (
        <div className="absolute bottom-2 right-2 space-x-2">
          <MediaActions
            url={url}
            mediaItem={mediaItem}
            variant="outline"
            copyLabel="Audio URL"
            downloadFileName={url.split("/").pop() || "audio"}
            className="flex gap-2"
          />
        </div>
      )}
    </div>
  );

  const content = (
    <div className="w-full h-full flex items-center justify-center p-4">
      <AudioPlayer
        url={url}
        title={title}
        duration={duration}
        autoPlay={autoPlay}
        preload={preload}
        onPlay={onPlay}
        onEnded={onEnded}
        onPause={onPause}
        className="w-full max-w-[600px]"
      />
    </div>
  );

  const handleCopyDescription = () => {
    if (description) {
      navigator.clipboard.writeText(description);
      toast("Transcript copied to clipboard");
    }
  };

  const actions = (
    <>
      {description && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleCopyDescription}
            >
              <Copy className="w-4 h-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Copy transcript</TooltipContent>
        </Tooltip>
      )}

      <MediaActions
        url={url}
        mediaItem={mediaItem}
        variant="ghost"
        size="icon"
        copyLabel="Copy audio URL"
        downloadFileName={url.split("/").pop() || "audio"}
      />
    </>
  );

  return (
    <MediaDialogComponent
      trigger={trigger}
      title={title || url.split("/").pop()?.split(".")[0] || "Audio"}
      actions={actions}
      metadata={metadata}
      description={description}
      dimensions={duration ? { width: undefined, height: undefined } : undefined}
    >
      {content}
    </MediaDialogComponent>
  );
};

export default AudioContent;
