import MediaDialog from "@/components/MediaDialog";
import { MediaActions } from "@/components/media/MediaActions";
import { VideoRenderer } from "@/components/media/VideoRenderer";
import { useMediaPlayer } from "@/hooks/useMediaPlayer";
import { MediaItem } from "@/types/media";
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
  className?: string;
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
  className,
}) => {
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
  }, [dialogId, registerPlayer, unregisterPlayer, playPlayer, url]);

  const fileName = url.split("/").pop() || "video.mp4";

  return (
    <MediaDialog
      trigger={
        <div className={className || "relative max-h-[400px] max-w-[500px] w-fit"}>
          <VideoRenderer
            url={url}
            autoPlay={autoPlay}
            controls={controls}
            loop={loop}
            muted={true}
            preload={preload}
            duration={duration}
            isThumbnail={true}
          />
          {showControls && (
            <div className="absolute bottom-2 right-2 space-x-2">
              <MediaActions
                url={url}
                mediaItem={mediaItem}
                variant="outline"
                copyLabel="Video URL"
                downloadFileName={fileName}
              />
            </div>
          )}
        </div>
      }
      title={caption || mediaItem?.name || "Video Details"}
      actions={
        <MediaActions
          url={url}
          mediaItem={mediaItem}
          variant="ghost"
          size="default"
          copyLabel="Video URL"
          downloadLabel="Download video"
          downloadFileName={fileName}
        />
      }
      metadata={metadata}
      description={description || mediaItem?.description}
    >
      <VideoRenderer
        ref={dialogVideoRef}
        url={url}
        autoPlay={true}
        controls={true}
        loop={true}
        muted={false}
        preload="auto"
        isThumbnail={false}
        className="w-full h-full"
      />
    </MediaDialog>
  );
};

export default memo(VideoContent);
