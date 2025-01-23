import { useRef, useEffect, memo } from "react";
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
  id?: string;
}

export function getMediaItems(messages: Message[]): MediaItem[] {
  // Extract media URLs from markdown image syntax and HTML audio/video tags
  const mediaItems = messages
    .filter((message) => message.type === "tool" || message.type === "human")
    .flatMap((message) => {
      const items: MediaItem[] = [];

      const body = Array.isArray(message.content)
        ? message.content
            .filter((item) => item.type === "text")
            .map((item) => item.text)
            .join("\n")
        : message.content;

      // Find any markdown image syntax within image tags, with optional id attribute and display wrapper
      // Allow for any content between image and display tags
      const imageMatches = body.matchAll(
        /<image(?:\s+id="([^"]*)")?>[^]*?<display>\s*!\[([^\]]*)\]\(([^)]+)\)\s*<\/display>[^]*?<\/image>/gs
      );
      for (const match of imageMatches) {
        const [_, id, alt, url] = match;
        const key = id
          ? `${message.tool_call_id}-${id}`
          : `${message.tool_call_id}-${url}`;

        items.push({
          key,
          type: "image",
          alt,
          url,
          toolCallId: message.tool_call_id,
          messageId: message.id,
          id,
        });
      }

      // Find HTML audio/video tags with direct src or nested source tags, capturing optional id
      const mediaMatches = body.matchAll(
        /<(audio|video)(?:\s+id="([^"]*)")?(?:[^>]*src="([^"]+)"[^>]*>|[^>]*>(?:[^<]*<source[^>]*src="([^"]+)"[^>]*>)?)/g
      );
      for (const match of mediaMatches) {
        const type = match[1]; // 'audio' or 'video'
        const id = match[2];
        const directSrc = match[3];
        const sourceSrc = match[4];
        const url = directSrc || sourceSrc;
        if (url) {
          const key = id
            ? `${message.tool_call_id}-${id}`
            : `${message.tool_call_id}-${url}`;
          items.push({
            key,
            type,
            url,
            messageId: message.id,
            content: typeof message.content === "string" ? message.content : "",
            id,
          });
        }
      }
      // @HACK to workaround the cursor port locking issue
      for (const item of items) {
        item.url = item.url.replace("5002", "5003");
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

  // Scroll effect remains the same...
  useEffect(() => {
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
    <div className={cn("flex flex-col", className)}>
      {mediaItems.map((item) => {
        if (item.type === "image") {
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
        if (item.type === "link") {
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
        if (item.type === "audio") {
          return (
            <AudioContent
              className="w-full"
              preload="auto"
              url={item.url}
              key={item.key}
            />
          );
        }
        if (item.type === "video") {
          return (
            <VideoContent
              url={item.url}
              autoPlay={true}
              muted={true}
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
