import { Message } from "../slices/messagesSlice";

export interface MediaItem {
  key: string;
  media_type: string;
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
        const [, id, alt, url] = match;
        const key = id
          ? `${message.tool_call_id}-${id}`
          : `${message.tool_call_id}-${url}`;

        items.push({
          key,
          media_type: "image",
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
            media_type: type,
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
