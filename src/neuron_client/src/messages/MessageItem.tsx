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
import { Loader2, AlertCircle } from "lucide-react";
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
    isOptimistic,
    error,
    isCancelled,
  } = message;

  // Get the message user from the users slice if available
  const messageUser = useAppSelector((state) =>
    user_id ? getUser(state, user_id) : null
  );

  // Don't render cancelled messages
  if (isCancelled) {
    return null;
  }

  const isTool = role === "tool" || node === "tools";
  const showToolOutput = isTool && toolOutput && toolOutput.includes(name ?? "");
  // Normalize artifact to always be an array for backward compatibility
  const normalizedArtifact = message.artifact
    ? Array.isArray(message.artifact)
      ? message.artifact
      : [message.artifact]
    : [];

  const hasMediaArtifact = role === 'tool' && normalizedArtifact.length > 0 && normalizedArtifact.some((a: { type: string }) => a.type === 'media');

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
            artifact={normalizedArtifact}
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
        "w-full my-2 rounded-md transition-opacity duration-200",
        role === "system" ? "bg-zinc-900" : "",
        role === "human" ? "border" : "",
        isOptimistic ? "opacity-70" : "",
        error ? "border-red-500" : ""
      )}
    >
      <div className="px-6 py-4 text-small text-default-400">
        {renderMessageContent()}

        {/* Message metadata footer */}
        <div className="flex justify-between items-center mt-2">
          {/* Error message on the left */}
          {error && (
            <div className="flex items-center gap-1 text-xs text-red-500">
              <AlertCircle className="h-3 w-3" />
              <span>{error}</span>
            </div>
          )}

          {/* Metadata on the right */}
          <div className="flex justify-end flex-1 space-x-2">
            {/* Show loading indicator for optimistic messages */}
            {isOptimistic && (
              <Tooltip delayDuration={0}>
                <TooltipTrigger>
                  <Loader2 className="h-3 w-3 animate-spin text-gray-500" />
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <span>Sending...</span>
                </TooltipContent>
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
    </div>
  );
};

export default memo(MessageItem);
