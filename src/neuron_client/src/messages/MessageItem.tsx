import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppSelector } from "@/hooks";
import {
  getMessage,
  getTextContent,
  getThinkingContent,
} from "@/slices/messagesSlice";
import { RootState } from "@/store";
import { useAuth0 } from "@auth0/auth0-react";
import { Bot, ChevronDown, ChevronUp, Hammer, User } from "lucide-react";
import React, { memo, useState } from "react";
import { formatNumber } from "../utils/numberFormat";
import Content from "./Content";
import TokenMetadataTable from "./TokenMetadataTable";

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
  const [isThinkingOpen, setIsThinkingOpen] = useState(true);
  const message = useAppSelector((state: RootState) =>
    getMessage(state, messageId)
  );

  const { user } = useAuth0();
  const { type: role, content, node, status = undefined } = message;
  const isTool = role === "tool" || node === "tools";
  const showToolOutput =
    isTool && toolOutput && toolOutput.includes(message.name ?? "");

  let body = getTextContent(content);
  const thinking = getThinkingContent(content);
  const hasThinking = thinking.trim().length > 0;

  if (!showTools) {
    body = body.replace(/<\|AI\|>[\s\S]*?<\|AI\|>/g, "").trim();
  }

  if (
    !showTools &&
    ((isTool && !showToolOutput) || (body.length === 0 && !hasThinking))
  ) {
    // If there are no media items or content, don't show anything
    return <div />;
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
          {hasThinking && (
            <Collapsible
              open={isThinkingOpen}
              onOpenChange={setIsThinkingOpen}
              className="mb-4 border bg-zinc-900 px-4 py-2 rounded-md"
            >
              <CollapsibleTrigger asChild>
                <div className="flex items-center justify-between cursor-pointer">
                  <div className="text-sm font-medium italic">Thinking</div>

                  <button className="rounded-full p-1 hover:bg-muted">
                    {isThinkingOpen ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="mt-4 mb-2 text-sm text-muted-foreground whitespace-pre-wrap">
                  {thinking}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

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
  return elements;
};

export default memo(MessageItem);
