import { useRef, useEffect, useState, memo } from "react";
import { cn } from "@/lib/utils";
import AudioContent from "./AudioContent";
import ImageContent from "./ImageContent";
import VideoContent from "./VideoContent";
import { Message } from "../slices/messagesSlice";
import { Button } from "@/components/ui/button";

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
    .filter((message) => message.type === "tool" || message.type === "human")
    .flatMap((message) => {
      const items: MediaItem[] = [];

      const body = Array.isArray(message.content)
        ? message.content
            .filter((item) => item.type === "text")
            .map((item) => item.text)
            .join("\n")
        : message.content;

      // Find any markdown image syntax within image tags, regardless of format
      const imageMatches = body.matchAll(
        /<image>.*?!\[([^\]]*)\]\(([^)]+)\).*?<\/image>/gs
      );
      for (const match of imageMatches) {
        const [_, alt, url] = match;
        const key = `${message.tool_call_id}-${url}`;

        items.push({
          key,
          type: "image",
          alt,
          url,
          toolCallId: message.tool_call_id,
          messageId: message.id,
        });
      }

      // Find markdown image and link tags ![alt](url) and [alt](url) surrounded by optional <link> or <image> tags
      const markdownMatches = body.matchAll(
        /<(link|image)>\s*\[([^\]]*)\]\(([^)]+)\)\s*<\/\1>/g
      );
      for (const match of markdownMatches) {
        const type = match[1];
        const key = `${message.tool_call_id}-${match[3]}`;
        let alt = match[2];
        let url = match[3];

        if (alt.match(/\.(py|js|txt|md)$/)) {
          alt = "View " + alt;
          url = `/code-viewer?url=${url}`;
        }

        items.push({
          key,
          type: type === "image" ? "image" : "link",
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
              className="w-full h-36"
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
