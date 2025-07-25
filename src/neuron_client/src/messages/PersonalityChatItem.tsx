import React from "react";
import { Bot, AlertCircle, Loader2, Edit, Pen } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import Content from "./Content";
import { PersonalityChatMessage } from "../types/personalityChat";
import { Personality } from "../types/personality";
import { useAppSelector } from "../hooks";
import { getUser } from "../slices/usersSlice";
import { getCurrentUser } from "../slices/appSlice";

interface PersonalityChatItemProps {
  message: PersonalityChatMessage;
  personality: Personality;
  onEditMessage?: (message: { id: string; content: string }) => void;
}

const PersonalityChatItem: React.FC<PersonalityChatItemProps> = ({
  message,
  personality,
  onEditMessage,
}) => {
  const currentUser = useAppSelector(getCurrentUser);
  const isCurrentUser = message.user_id === currentUser?.sub;
  const isPersonality = message.user_id === null;
  const isOptimistic = 'isOptimistic' in message && message.isOptimistic;
  const hasError = 'error' in message && message.error;

  // Check if message has been edited (created_at != updated_at)
  const isEdited = !isOptimistic && 'created_at' in message && 'updated_at' in message &&
    message.created_at !== message.updated_at;

  // Get user data from Redux store
  const user = useAppSelector((state) =>
    message.user_id ? getUser(state, message.user_id) : null
  );

  // Create display name and avatar letter
  const displayName = user?.nickname || "Unknown User";
  const avatarLetter = user?.nickname?.[0]?.toUpperCase() || "U";

  // Format timestamp
  const timestamp = typeof message.created_at === 'string'
    ? new Date(message.created_at)
    : new Date(message.created_at);

  // Render personality messages with original layout
  if (isPersonality) {
    return (
      <div className="mb-6 group">
        <div className="flex items-start space-x-2">
          {/* Avatar */}
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <div className="w-10 h-10 mr-4 rounded-full flex items-center justify-center min-w-[40px] bg-primary">
                <Avatar>
                  <AvatarImage src={personality.logo || ""} />
                  <AvatarFallback>
                    <Bot className="text-primary-foreground" size={20} />
                  </AvatarFallback>
                </Avatar>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right">
              {personality.name}
            </TooltipContent>
          </Tooltip>

          {/* Message Content */}
          <div className="flex-1 space-y-2">
            {/* Message Header */}
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <span className="font-medium">
                {personality.name}
              </span>
              <span>•</span>
              <FuzzyTimeAgo timestamp={timestamp.getTime()} />
            </div>

            {/* Message Body */}
            <div className="prose prose-sm max-w-none break-words">
              <Content content={message.content} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render user messages with chat bubble layout (all left-aligned)
  return (
    <div className="mb-4 group">
      <div className="flex items-end gap-2 max-w-4xl justify-start">
        {/* Avatar (always on left side) */}
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center min-w-[32px] mb-1",
              isCurrentUser ? "bg-primary" : "bg-muted"
            )}>
              <Avatar className="w-8 h-8">
                <AvatarImage src={user?.picture || ""} />
                <AvatarFallback>
                  <span className={cn(
                    "text-xs font-medium",
                    isCurrentUser ? "text-primary-foreground" : "text-muted-foreground"
                  )}>
                    {avatarLetter}
                  </span>
                </AvatarFallback>
              </Avatar>
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            {displayName}
          </TooltipContent>
        </Tooltip>

        {/* Chat Bubble */}
        <div className={cn(
          "relative max-w-md px-4 pb-2 pt-2 rounded-sm break-words",
          isCurrentUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}>
          {/* Message Content */}
          <div className={cn(
            "prose prose-sm max-w-none break-words",
            isCurrentUser ? "prose-invert" : "",
            isOptimistic && "opacity-70",
            hasError && "text-destructive opacity-70"
          )}>
            <Content content={message.content} />
          </div>

          {/* Timestamp and edit button */}
          <div className={cn(
            "flex items-center justify-end mt-2 text-xs gap-2",
            isCurrentUser ? "text-primary-foreground/70" : "text-muted-foreground"
          )}>
            {/* Status indicators */}
            {isOptimistic && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Loader2 className="h-3 w-3 animate-spin" />
                </TooltipTrigger>
                <TooltipContent>Sending...</TooltipContent>
              </Tooltip>
            )}

            {hasError && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <AlertCircle className="h-3 w-3 text-destructive" />
                </TooltipTrigger>
                <TooltipContent>
                  Failed to send: {hasError}
                </TooltipContent>
              </Tooltip>
            )}

            {/* Edit button for current user messages */}
            {isCurrentUser && !isOptimistic && !hasError && onEditMessage && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onEditMessage({ id: message.id, content: message.content })}
                    className={cn(
                      "p-0.5 rounded hover:bg-black/10",
                      isCurrentUser ? "hover:bg-white/10" : "hover:bg-black/10"
                    )}
                  >
                    <Edit className="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Edit message</TooltipContent>
              </Tooltip>
            )}

            {/* Edited indicator */}
            {isEdited && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Pen className="h-3 w-3" />
                </TooltipTrigger>
                <TooltipContent>Message edited</TooltipContent>
              </Tooltip>
            )}

            <FuzzyTimeAgo timestamp={timestamp.getTime()} />
          </div>

          {/* Error message */}
          {hasError && (
            <div className="text-sm text-destructive mt-2">
              Failed to send message. Please try again.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PersonalityChatItem;
