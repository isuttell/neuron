import { MediaListDropdown } from "@/components/MediaListDropdown";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useToast } from "@/hooks/use-toast";
import { useMediaPlayer } from "@/hooks/useMediaPlayer";
import { MediaItem } from "@/types/media";
import { Copy, Download, Info } from "lucide-react";
import React, { memo, useEffect, useId, useRef } from "react";
interface VideoContentProps {
  url: string;
  autoPlay?: boolean;
  controls?: boolean;
  loop?: boolean;
  showControls?: boolean;
  mediaItem?: MediaItem;
  caption?: string;
  description?: string;
  duration?: number;
  metadata?: Record<string, unknown>;
  preload?: "none" | "metadata" | "auto";
}

const VideoContent: React.FC<VideoContentProps> = ({
  url,
  mediaItem,
  autoPlay = false,
  controls = false,
  loop = false,
  showControls = false,
  caption,
  description,
  duration,
  metadata,
  preload = "metadata",
}) => {
  const { toast } = useToast();
  const thumbnailId = useId();
  const dialogId = useId();
  const dialogVideoRef = useRef<HTMLVideoElement>(null);
  const { registerPlayer, unregisterPlayer, playPlayer } = useMediaPlayer();

  useEffect(() => {
    const dialogVideo = dialogVideoRef.current;

    if (dialogVideo) {
      registerPlayer(dialogId, url, dialogVideo);
      dialogVideo.addEventListener("play", () => playPlayer(dialogId));
    }

    return () => {
      if (dialogVideo) {
        unregisterPlayer(dialogId, url);
      }
    };
  }, [
    thumbnailId,
    dialogId,
    registerPlayer,
    unregisterPlayer,
    playPlayer,
    url,
  ]);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <div className="relative max-h-[400px] max-w-[500px] w-fit">
          <video
            className="rounded-lg w-full h-full object-contain cursor-pointer"
            src={url}
            autoPlay={autoPlay}
            muted={true}
            controls={controls}
            loop={loop}
            preload={preload}
          />
          {duration && (
            <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
              {Math.floor(duration / 60)}:{(Math.floor(duration) % 60).toString().padStart(2, '0')}
            </div>
          )}
          {showControls && (
            <div className="absolute bottom-2 right-2 space-x-2">
              {mediaItem && (
                <MediaListDropdown
                  variant="outline"
                  mediaItemId={mediaItem.id}
                />
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    className=""
                    variant="outline"
                    onClick={(e) => {
                      e.preventDefault();
                      navigator.clipboard.writeText(url);
                      toast({
                        title: "Video URL copied to clipboard",
                      });
                    }}
                  >
                    <Copy />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Copy video URL</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
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
                      <Download />
                    </a>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download video</TooltipContent>
              </Tooltip>
              {metadata && Object.keys(metadata).length > 0 && (
                <Popover>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                        >
                          <Info />
                        </Button>
                      </PopoverTrigger>
                    </TooltipTrigger>
                    <TooltipContent>View metadata</TooltipContent>
                  </Tooltip>
                  <PopoverContent className="w-80">
                    <div className="space-y-2">
                      <h4 className="font-medium text-sm">Generation Details</h4>
                      <div className="text-sm space-y-1">
                        {metadata.model ? (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Model:</span>
                            <span className="font-mono text-xs">
                            {String(metadata.model)}
                          </span>
                          </div>
                        ) : null}
                        {metadata.duration ? (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Duration:</span>
                            <span>{Math.floor((metadata.duration as number) / 60)}:{(Math.floor(metadata.duration as number) % 60).toString().padStart(2, '0')}</span>
                          </div>
                        ) : null}
                        {metadata.fps ? (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">FPS:</span>
                            <span>
                            {String(metadata.fps)}
                          </span>
                          </div>
                        ) : null}
                        {metadata.format ? (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Format:</span>
                            <span>
                            {String(metadata.format)}
                          </span>
                          </div>
                        ) : null}
                        {metadata.seed ? (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Seed:</span>
                            <span className="font-mono text-xs">
                            {String(metadata.seed)}
                          </span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              )}
            </div>
          )}
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>{caption || mediaItem?.name || "Video Details"}</DialogTitle>
          {(description || mediaItem?.description) && (
            <DialogDescription>{description || mediaItem?.description}</DialogDescription>
          )}
        </DialogHeader>
        <div className="flex-1 overflow-hidden">
          <video
            ref={dialogVideoRef}
            className="w-full h-full rounded-md object-contain"
            autoPlay={true}
            controls={true}
            loop={true}
            playsInline
            muted={false}
          >
            <source src={url} type="video/mp4" />
          </video>
        </div>
        <div className="flex justify-end gap-2">
          {mediaItem && (
            <MediaListDropdown variant="outline" mediaItemId={mediaItem.id} />
          )}
          <Button
            variant="outline"
            onClick={(e) => {
              e.preventDefault();
              navigator.clipboard.writeText(url);
              toast({
                title: "Video URL copied to clipboard",
              });
            }}
          >
            <Copy /> Copy
          </Button>
          <Button variant="outline" asChild>
            <a
              className="text-primary"
              href={url}
              download
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download className="w-4 h-4" />
              Download
            </a>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default memo(VideoContent);
