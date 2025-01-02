import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import AudioContent from "./AudioContent";
import ImageContent from "./ImageContent";
import VideoContent from "./VideoContent";
import { Message } from "../slices/messagesSlice";
interface MediaItem {
  key: string;
  type: string;
  url: string;
  messageId: string;
  content?: string;
  alt?: string;
  toolCallId?: string;
}

export function getMediaItems(messages: Message[]): MediaItem[] {
  // Extract media URLs from markdown image syntax and HTML audio/video tags
  const mediaItems = messages
    .filter((message) => message.type === "tool")
    .flatMap((message) => {
      const items: MediaItem[] = [];

      const body = Array.isArray(message.content)
        ? message.content
            .filter((item) => item.type === "text")
            .map((item) => item.text)
            .join("\n")
        : message.content;

      // Find markdown image and link tags ![alt](url) and [alt](url)
      const matches = body.matchAll(/\[([^\]]*)\]\(([^)]+)\)/g);
      for (const match of matches) {
        const key = `${message.tool_call_id}-${match[2]}`;
        let alt = match[1];
        let url = match[2];

        if (alt.match(/\.(py|js|txt|md)$/)) {
          alt = "View " + alt;
          url = `/code-viewer?url=${url}`;
        }

        items.push({
          key,
          type: /\.(jpeg|jpg|png|gif|svg)$/.test(url) ? "image" : "link",
          alt,
          url,
          toolCallId: message.tool_call_id,
          messageId: message.id,
        });
      }

      // Find HTML audio/video tags with direct src or nested source tags
      const mediaMatches = body.matchAll(
        /<(audio|video)(?:[^>]*src="([^"]+)"[^>]*>|[^>]*>(?:[^<]*<source[^>]*src="([^"]+)"[^>]*>)?)/g
      );
      for (const match of mediaMatches) {
        const type = match[1]; // 'audio' or 'video'
        const directSrc = match[2];
        const sourceSrc = match[3];
        if (directSrc || sourceSrc) {
          items.push({
            key: `${message.tool_call_id}-${directSrc || sourceSrc}`,
            type,
            url: directSrc || sourceSrc,
            messageId: message.id,
            content: typeof message.content === "string" ? message.content : "",
          });
        }
      }

      return items;
    });

  return Array.from(
    new Map(mediaItems.map((item) => [item.key, item])).values()
  );
}

interface MediaListProps {
  className?: string;
  mediaItems: MediaItem[];
  threadId: string;
  thumbnail_size?: "t" | "l" | "xl";
}

export function MediaList({
  className,
  mediaItems,
  threadId,
  thumbnail_size = "t",
}: MediaListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Scroll to the bottom of the messages when they change
    setTimeout(() => {
      if (endRef.current) {
        endRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, 0);
  }, [
    mediaItems.length,
    mediaItems.length > 0 && mediaItems[mediaItems.length - 1].content,
    endRef.current,
    threadId,
  ]);

  return (
    <div className={cn("flex", className)}>
      {mediaItems.map((item) => (
        <div key={item.key}>
          {item.type === "image" ? (
            <ImageContent
              url={item.url}
              alt={item.alt}
              width={1024}
              height={1024}
              thumbnail_size={thumbnail_size}
              preload={true}
            />
          ) : null}
          {item.type === "link" ? (
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              {item.alt}
            </a>
          ) : null}
          {item.type === "audio" ? (
            <AudioContent className="w-full" preload="auto" url={item.url} />
          ) : null}
          {item.type === "video" ? (
            <VideoContent
              url={item.url}
              autoPlay={true}
              muted={true}
              controls={false}
              loop={true}
            />
          ) : null}
        </div>
      ))}
      {mediaItems.length === 0 && (
        <div className="m-4 text-center text-muted-foreground">
          No media found
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

export default MediaList;
