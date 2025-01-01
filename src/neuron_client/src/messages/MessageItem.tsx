import React, { memo } from "react";
import { Bot, User, Hammer } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Message } from "@/slices/messagesSlice";
import Content from "./Content";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import { formatNumber } from "../utils/numberFormat";
import TokenMetadataTable from "./TokenMetadataTable";

interface MessageItemProps {
  message: Message;
  onPromptClick?: (prompt: string) => void;
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
  message,
  onPromptClick,
}) => {
  const { type: role, content, status = undefined } = message;

  const body = Array.isArray(content)
    ? content
        .filter((item) => item.type === "text")
        .map((item) => item.text)
        .join("\n")
    : content;

  return (
    <Card
      className={`w-full mb-2 ${
        role === "tool" || role === "system" ? "bg-zinc-900" : ""
      }`}
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
                <User className="text-muted-foreground" size={20} />
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
            <Content
              content={body}
              preload={status === "streaming" ? "none" : "auto"}
              onPromptClick={onPromptClick}
            />
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
    </Card>
  );
};

export default memo(MessageItem);
