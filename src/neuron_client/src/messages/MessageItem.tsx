import React, { memo } from "react";
import { Bot, User, Hammer } from "lucide-react";
import { AttachmentIndicator } from "@/components/AttachmentIndicator";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getMessage, getTextContent } from "@/slices/messagesSlice";
import Content from "./Content";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import { formatNumber } from "../utils/numberFormat";
import TokenMetadataTable from "./TokenMetadataTable";
import { getMediaItems } from "../utils/mediaUtils";
import MediaList from "./MediaList";
import { useAuth0 } from "@auth0/auth0-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { RootState } from "@/store";
import { useAppSelector } from "@/hooks";

interface MessageItemProps {
  messageId: string;
  onPromptClick?: (prompt: string) => void;
  showTools?: boolean;
  toolOutput?: string[];
}

const getStatusMessage = (status: string) => {
  if (status === "thinking") {
    return "Thinking...";
  } else if (status === "tools") {
    return "Looking up more information...";
  } else if (status === "streaming") {
    return "Streaming...";
  } else {
    return status;
  }
};

const MessageItem: React.FC<MessageItemProps> = ({
  messageId,
  onPromptClick,
  showTools = false,
  toolOutput = ["deepseek_reasoning"],
}) => {
  const message = useAppSelector((state: RootState) =>
    getMessage(state, messageId)
  );

  const { user } = useAuth0();
  const { type: role, content, node, status = undefined } = message;
  const isTool = role === "tool" || node === "tools";
  const showToolOutput =
    isTool && toolOutput && toolOutput.includes(message.name ?? "");

  let body = getTextContent(content);

  if (!showTools) {
    body = body.replace(/<\|AI\|>[\s\S]*?<\|AI\|>/g, "").trim();
  }

  const mediaItems = getMediaItems([message]);

  if (!showTools && ((isTool && !showToolOutput) || body.length === 0)) {
    if (mediaItems.length === 0) {
      // If there are no media items, don't show the tool card
      return <div />;
    }
    // If there are media items, show the media list but not the raw content
    return (
      <MediaList
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 ml-[5.5rem]"
        mediaItems={getMediaItems([message])}
        threadId={message.thread_id}
        showControls
      />
    );
  }

  const elements = [
    <Card
      key={message.id}
      className={`w-full my-2 ${role === "system" ? "bg-zinc-900" : ""}`}
    >
      <CardContent className="px-6 py-4 text-small text-default-400 flex items-start space-x-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <div
              className={`w-10 h-10 mr-4 ${
                role === "human" ? "bg-muted" : "bg-primary"
              } rounded-full flex items-center justify-center min-w-[40px]`}
            >
              {role === "human" ? (
                <Avatar>
                  <AvatarImage src={user?.picture} />
                  <AvatarFallback>
                    <User className="text-muted-foreground" size={20} />
                  </AvatarFallback>
                </Avatar>
              ) : null}
              {role === "ai" || role === "system" ? (
                <Bot className="text-primary-foreground" size={20} />
              ) : null}
              {role === "tool" ? (
                <Hammer className="text-primary-foreground" size={20} />
              ) : null}
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            {role === "human" ? "You" : "AI"}
          </TooltipContent>
        </Tooltip>
        <div className="flex flex-col flex-1 ">
          {body.trim().length > 0 ? (
            !showTools ? (
              <Content
                content={body}
                preload={status === "streaming" ? "none" : "auto"}
                onPromptClick={onPromptClick}
              />
            ) : (
              <div className="whitespace-pre-wrap">{body}</div>
            )
          ) : (
            <div className="space-y-2 flex-1">
              <Skeleton className="h-4 w-[250px]" />
              <Skeleton className="h-4 w-[200px]" />
              {status && status !== "streaming" && (
                <p className="text-sm text-gray-500">
                  {getStatusMessage(status)}
                </p>
              )}
            </div>
          )}
          <div className="flex justify-end flex-shrink-0 space-x-2">
            {typeof message.node === "string" && message.node !== "agent" && (
              <Tooltip delayDuration={0}>
                <TooltipTrigger>
                  <span className="text-xs text-gray-500">{message.node}</span>
                </TooltipTrigger>
                <TooltipContent side="bottom">Node</TooltipContent>
              </Tooltip>
            )}
            {message.usage_metadata?.total_tokens &&
              message.usage_metadata.total_tokens > 0 && (
                <Tooltip delayDuration={0}>
                  <TooltipTrigger>
                    <span className="text-xs text-gray-500">
                      {formatNumber(message.usage_metadata.total_tokens)}
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    <TokenMetadataTable
                      input_tokens={message.usage_metadata.input_tokens ?? 0}
                      output_tokens={message.usage_metadata.output_tokens ?? 0}
                      total_tokens={message.usage_metadata.total_tokens ?? 0}
                    />
                  </TooltipContent>
                </Tooltip>
              )}
            {message.created_at && (
              <Tooltip delayDuration={0}>
                <TooltipTrigger>
                  <FuzzyTimeAgo
                    className="text-xs text-gray-500"
                    timestamp={message.created_at}
                  />
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <span className="p-4">
                    {new Date(message.created_at).toLocaleString()}
                  </span>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>
      </CardContent>
    </Card>,
  ];
  if (mediaItems.length > 0) {
    const hasAudio = mediaItems.some((item) => item.media_type === "audio");
    const hasFiles = mediaItems.some((item) =>
      ["image", "video", "link"].includes(item.media_type)
    );

    if (hasAudio || hasFiles) {
      elements.push(
        <div key={`${message.id}-indicators`} className="ml-[5.5rem] mb-2">
          {hasAudio && (
            <AttachmentIndicator
              type="audio"
              onRemove={() => {}} // Read-only in thread view
            />
          )}
          {hasFiles && (
            <AttachmentIndicator
              type="file"
              onRemove={() => {}} // Read-only in thread view
            />
          )}
        </div>
      );
    }

    elements.push(
      <MediaList
        key={`${message.id}-media`}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 ml-[5.5rem]"
        mediaItems={mediaItems}
        threadId={message.thread_id}
      />
    );
  }
  return elements;
};

export default memo(MessageItem);
