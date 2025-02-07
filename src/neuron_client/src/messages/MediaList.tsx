import { useRef, useEffect, memo, useCallback } from "react";
import { cn } from "@/lib/utils";
import AudioContent from "./AudioContent";
import ImageContent from "./ImageContent";
import VideoContent from "./VideoContent";
import { MediaItem } from "@/utils/mediaUtils";

interface MediaListProps {
  className?: string;
  mediaItems: MediaItem[];
  threadId: string;
  thumbnail_size?: "t" | "l" | "xl";
  showControls?: boolean;
  autoPlay?: boolean;
}

function MediaList({
  className,
  mediaItems,
  threadId,
  thumbnail_size = "t",
  showControls = false,
}: MediaListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  const scrollToEnd = useCallback(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(scrollToEnd, 0);
    return () => clearTimeout(timer);
  }, [scrollToEnd, mediaItems.length, threadId]);

  return (
    <div className={cn("flex flex-col", className)}>
      {mediaItems.map((item) => {
        if (item.media_type === "image") {
          return (
            <ImageContent
              key={item.key}
              url={item.url}
              alt={item.alt}
              width={1024}
              height={1024}
              thumbnail_size={thumbnail_size}
              showControls={showControls}
              objectFit="contain"
            />
          );
        }
        if (item.media_type === "link") {
          return (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              key={item.key}
            >
              {item.alt}
            </a>
          );
        }
        if (item.media_type === "audio") {
          return (
            <AudioContent
              className="w-full"
              preload="auto"
              url={item.url}
              key={item.key}
            />
          );
        }
        if (item.media_type === "video") {
          return (
            <VideoContent
              url={item.url}
              autoPlay={true}
              controls={false}
              loop={true}
              key={item.key}
              showControls={showControls}
            />
          );
        }
        return null;
      })}
      {mediaItems.length === 0 && (
        <div className="m-4 text-center text-muted-foreground">
          No media found
        </div>
      )}
      <div className="flex-1" />
      <div ref={endRef} />
    </div>
  );
}

export default memo(MediaList);
