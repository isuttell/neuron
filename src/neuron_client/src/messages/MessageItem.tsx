import React, { memo } from "react";
import { Bot, User, Hammer } from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Message } from "@/slices/messagesSlice";
import Content from "./Content";
interface MessageItemProps {
  message: Message;
}

const getFuzzyTime = (date: Date) => {
  const now = new Date();
  const secondsPast = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (secondsPast < 60) {
    return "Just now";
  }
  if (secondsPast < 3600) {
    return `${Math.floor(secondsPast / 60)}m`;
  }
  if (secondsPast <= 86400) {
    return `${Math.floor(secondsPast / 3600)}h`;
  }
  if (secondsPast <= 2592000) {
    return `${Math.floor(secondsPast / 86400)}d`;
  }
  if (secondsPast <= 31536000) {
    return `${Math.floor(secondsPast / 2592000)}mo`;
  }
  return `${Math.floor(secondsPast / 31536000)}y`;
};

const getStatusMessage = (status: string) => {
  if (status === "thinking") {
    return "Thinking...";
  } else if (status === "tools") {
    return "Looking up more information...";
  } else if (status === "streaming") {
    return "Streaming...";
  } else {
    return "";
  }
};

const MessageItem: React.FC<MessageItemProps> = ({
  message: { role, content, created_at, status = undefined },
}) => {
  return (
    <Card
      className={`w-full mb-2 ${
        role === "tool" || role === "system" ? "bg-zinc-900" : ""
      }`}
    >
      <CardContent className="pb-1 px-6 pt-6 text-small text-default-400 flex items-start space-x-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={`w-10 h-10 mr-4 ${
                role === "human" ? "bg-accent" : "bg-primary"
              } rounded-full flex items-center justify-center min-w-[40px]`}
            >
              {role === "human" ? (
                <User className="text-white" size={20} />
              ) : null}
              {role === "ai" || role === "system" ? (
                <Bot className="text-black" size={20} />
              ) : null}
              {role === "tool" ? (
                <Hammer className="text-black" size={20} />
              ) : null}
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            {role === "human" ? "You" : "AI"}
          </TooltipContent>
        </Tooltip>

        {(!status || status === "streaming") && content.trim().length > 0 ? (
          <Content
            content={content}
            preload={status === "streaming" ? "none" : "auto"}
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
      </CardContent>
      <CardFooter className="gap-3">
        <div className="flex gap-1 flex-1 text-gray-500 space-x-2">
          <div className="flex-1" />
          <Tooltip>
            <TooltipTrigger asChild>
              <p className="text-sm hover:text-gray-700">
                {getFuzzyTime(new Date(created_at))}
              </p>
            </TooltipTrigger>
            <TooltipContent side="right">
              {new Date(created_at).toLocaleString()}
            </TooltipContent>
          </Tooltip>
        </div>
      </CardFooter>
    </Card>
  );
};

export default memo(MessageItem);
