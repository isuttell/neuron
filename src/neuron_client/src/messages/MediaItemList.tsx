import { useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import AudioContent from "./AudioContent";
import ImageContent from "./ImageContent";
import VideoContent from "./VideoContent";
import { MediaItem } from "@/types/media";

interface MediaListProps {
  className?: string;
  mediaItems: MediaItem[];
  thumbnail_size?: "t" | "l" | "xl";
  showControls?: boolean;
  autoPlay?: boolean;
}

function MediaItemList({
  className,
  mediaItems,
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
  }, [scrollToEnd, mediaItems.length]);

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {mediaItems.map((item) => {
        if (item.media_type === "image") {
          return (
            <ImageContent
              key={item.id}
              url={item.url}
              alt={item.name}
              description={item.description}
              width={1024}
              height={1024}
              thumbnail_size={thumbnail_size}
              showControls={showControls}
              objectFit="contain"
              mediaItem={item}
            />
          );
        }
        if (
          item.media_type === "link" ||
          item.media_type === "data" ||
          item.media_type === "code"
        ) {
          let url = item.url;
          if (item.media_type === "code" || item.media_type === "data") {
            url = `/code-viewer?url=${url}`;
          }
          return (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              key={item.id}
            >
              {item.name}
            </a>
          );
        }
        if (item.media_type === "audio") {
          return (
            <AudioContent
              className="w-full"
              preload="auto"
              url={item.url}
              title={item.name}
              description={item.description}
              key={item.id}
              mediaItem={item}
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
              key={item.id}
              showControls={showControls}
              mediaItem={item}
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

export default MediaItemList;
