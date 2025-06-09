import React, { memo } from "react";
import { useAppSelector } from "@/hooks";
import { getMessage } from "@/slices/messagesSlice";
import { getUser } from "@/slices/usersSlice";
import { RootState } from "@/store";
import { cn } from "@/lib/utils";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatNumber } from "../utils/numberFormat";
import TokenMetadataTable from "./TokenMetadataTable";
import ToolMessage from "./ToolMessage";
import AssistantMessage from "./AssistantMessage";
import HumanMessage from "./HumanMessage";
import SystemMessage from "./SystemMessage";
interface MessageItemProps {
  messageId: string;
  onPromptClick?: (prompt: string) => void;
  showTools?: boolean;
  toolOutput?: string[];
}

const MessageItem: React.FC<MessageItemProps> = ({
  messageId,
  onPromptClick,
  showTools = false,
  toolOutput = ["deepseek_reasoning"],
}) => {
  const message = useAppSelector((state: RootState) =>
    getMessage(state, messageId)
  );

  const {
    type: role,
    node,
    status,
    name,
    textContent,
    thinkingContent,
    user_id,
    citations,
    content,
  } = message;

  // Get the message user from the users slice if available
  const messageUser = useAppSelector((state) =>
    user_id ? getUser(state, user_id) : null
  );

  const isTool = role === "tool" || node === "tools";
  const showToolOutput = isTool && toolOutput && toolOutput.includes(name ?? "");
  const hasMediaArtifact = role === 'tool' && message.artifact?.type === 'media';

  // Skip rendering tool messages based on conditions
  if (
    !showTools &&
    isTool &&
    !showToolOutput &&
    !hasMediaArtifact
  ) {
    return <div />;
  }
  // Render the appropriate message component based on role
  const renderMessageContent = () => {
    switch (role) {
      case "tool":
        return (
          <ToolMessage
            name={name}
            textContent={textContent}
            artifact={message.artifact}
            showTools={showTools}
            status={status}
          />
        );
      case "human":
        return (
          <HumanMessage
            textContent={textContent}
            content={content}
            showTools={showTools}
            status={status}
            onPromptClick={onPromptClick}
            user={messageUser || undefined}
          />
        );
      case "system":
        return (
          <SystemMessage
            textContent={textContent}
            showTools={showTools}
            status={status}
            onPromptClick={onPromptClick}
          />
        );
      case "ai":
      default:
        return (
          <AssistantMessage
            textContent={textContent}
            thinkingContent={thinkingContent}
            citations={citations}
            content={content}
            showTools={showTools}
            status={status}
            onPromptClick={onPromptClick}
          />
        );
    }
  };

  return (
    <div
      key={message.id}
      className={cn(
        "w-full my-2 rounded-md",
        role === "system" ? "bg-zinc-900" : "",
        role === "human" ? "border" : ""
      )}
    >
      <div className="px-6 py-4 text-small text-default-400">
        {renderMessageContent()}

        {/* Message metadata footer */}
        <div className="flex justify-end mt-2 space-x-2">
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
                    input_token_details={message.usage_metadata.input_token_details as { cache_creation?: number; cache_read?: number } | undefined}
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
    </div>
  );
};

export default memo(MessageItem);
