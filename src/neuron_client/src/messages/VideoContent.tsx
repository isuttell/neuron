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
import { useToast } from "@/hooks/use-toast";
import { useMediaPlayer } from "@/hooks/useMediaPlayer";
import { MediaItem } from "@/types/media";
import { Copy, Download } from "lucide-react";
import { memo, useEffect, useId, useRef } from "react";
interface VideoContentProps {
  url: string;
  autoPlay?: boolean;
  controls?: boolean;
  loop?: boolean;
  showControls?: boolean;
  mediaItem?: MediaItem;
}

const VideoContent: React.FC<VideoContentProps> = ({
  url,
  mediaItem,
  autoPlay = false,
  controls = false,
  loop = false,
  showControls = false,
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
        <div className="w-full relative max-h-[1024px] max-w-[1024px]">
          <video
            className="rounded-lg w-full h-full object-contain cursor-pointer"
            src={url}
            autoPlay={autoPlay}
            muted={true}
            controls={controls}
            loop={loop}
          />
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
            </div>
          )}
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>{mediaItem?.name || "Video Details"}</DialogTitle>
          {mediaItem?.description && (
            <DialogDescription>{mediaItem.description}</DialogDescription>
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
                title: "Image URL copied to clipboard",
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
