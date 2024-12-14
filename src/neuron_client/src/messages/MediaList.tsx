import { useRef, useEffect } from "react";
import { Message } from "../slices/messagesSlice";
import { cn } from "@/lib/utils";
import AudioPlayer from "./AudioPlayer";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import Content from "./Content";
import ImageContent from "./ImageContent";

interface MediaListProps {
  className?: string;
  messages: Message[];
  threadId: string;
}

export function MediaList({ className, messages, threadId }: MediaListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Scroll to the bottom of the messages when they change
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [
    messages.length,
    messages.length > 0 && messages[messages.length - 1].content,
    endRef.current,
    threadId,
  ]);

  // Extract media URLs from markdown image syntax and HTML audio/video tags
  const mediaItems = messages
    .filter((message) => message.type === "tool")
    .flatMap((message) => {
      const items = [];

      const body = Array.isArray(message.content)
        ? message.content
            .filter((item) => item.type === "text")
            .map((item) => item.text)
            .join("\n")
        : message.content;

      // Find markdown image tags ![alt](url)
      const imageMatches = body.matchAll(/!\[([^\]]*)\]\(([^)]+)\)/g);
      for (const match of imageMatches) {
        items.push({
          type: "image",
          alt: match[1],
          url: match[2],
          messageId: message.id,
          message: message,
          // timestamp: message.created_at,
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
            type,
            url: directSrc || sourceSrc,
            messageId: message.id,
            content: message.content,
          });
        }
      }

      return items;
    });
  return (
    <div className={cn("flex flex-col m-2 overflow-y-auto", className)}>
      <div className="text-lg font-semibold p-4 ">Media</div>
      <div className="flex flex-1 flex-wrap relative">
        <div className="flex-1 absolute top-0 left-0 right-0 bottom-0 p-4 overflow-y-auto">
          {mediaItems.map((item) => (
            <div key={item.messageId} className="mb-4">
              {item.type === "image" ? (
                <ImageContent
                  url={item.url}
                  alt={item.alt}
                  width={1024}
                  height={1024}
                />
              ) : null}
              {item.type === "audio" ? (
                <Tooltip delayDuration={0}>
                  <TooltipTrigger className="w-full">
                    <AudioPlayer
                      className="w-full"
                      preload="auto"
                      src={item.url}
                    />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[512px] p-4">
                    <Content
                      content={
                        Array.isArray(item.content)
                          ? item.content[0].text
                          : item.content || ""
                      }
                      preload="none"
                    />
                  </TooltipContent>
                </Tooltip>
              ) : null}
              {item.type === "video" ? (
                <video className="w-full" controls src={item.url} />
              ) : null}
            </div>
          ))}
          {mediaItems.length === 0 && (
            <div className="text-center text-gray-500 text-sm">No media</div>
          )}
          <div ref={endRef} />
        </div>
      </div>
    </div>
  );
}

export default MediaList;
