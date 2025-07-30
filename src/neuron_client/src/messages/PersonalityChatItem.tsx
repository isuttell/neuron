import React from "react";
import { Bot, AlertCircle, Loader2, Edit, Pen } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import FuzzyTimeAgo from "@/components/FuzzyTimeAgo";
import Content from "./Content";
import MediaItems from "./MediaItems";
import { PersonalityChatMessage } from "../types/personalityChat";
import { Personality } from "../types/personality";
import { useAppSelector } from "../hooks";
import { getUser } from "../slices/usersSlice";
import { getCurrentUser } from "../slices/appSlice";
import { getRoomUsers } from "../slices/personalityRoomSlice";

interface PersonalityChatItemProps {
  message: PersonalityChatMessage;
  personality: Personality;
  roomId?: string;
  onEditMessage?: (message: { id: string; content: string }) => void;
}

const generateInitials = (nickname: string | null | undefined): string => {
  if (!nickname) return "U";

  // First try splitting by common delimiters (spaces, dashes, underscores)
  const delimiterSplit = nickname.split(/[\s\-_]+/).filter(part => part.length > 0);

  if (delimiterSplit.length >= 2) {
    return delimiterSplit.slice(0, 3).map(part => part[0].toUpperCase()).join("");
  }

  // If no delimiters, try splitting by camelCase (capital letters)
  const camelCaseSplit = nickname.split(/(?=[A-Z])/).filter(part => part.length > 0);

  if (camelCaseSplit.length >= 2) {
    return camelCaseSplit.slice(0, 3).map(part => part[0].toUpperCase()).join("");
  }

  // Fall back to just the first letter
  return nickname[0].toUpperCase();
};


const PersonalityChatItem: React.FC<PersonalityChatItemProps> = ({
  message,
  personality,
  roomId,
  onEditMessage,
}) => {
  const currentUser = useAppSelector(getCurrentUser);
  const isCurrentUser = message.user_id === currentUser?.sub;

  // Get room users for color assignment
  const roomUsers = useAppSelector((state) =>
    roomId ? getRoomUsers(state, roomId) : []
  );

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

  // Color palette for user avatars
  const userColors = [
    "bg-blue-500 text-white",
    "bg-green-500 text-white",
    "bg-purple-500 text-white",
    "bg-orange-500 text-white",
    "bg-pink-500 text-white",
    "bg-indigo-500 text-white",
    "bg-teal-500 text-white",
    "bg-amber-500 text-white"
  ];

  // Get user's color based on position in room users list
  const getUserColor = () => {
    if (isCurrentUser) return "bg-primary text-primary-foreground";
    if (!message.user_id || !roomUsers.length) return "bg-muted text-foreground";

    const userIndex = roomUsers.findIndex(roomUser => roomUser.user_id === message.user_id);
    if (userIndex === -1) return "bg-muted text-foreground";

    return userColors[userIndex % userColors.length];
  };

  // Get username text color to match avatar background
  const getUsernameColor = () => {
    if (isCurrentUser) return "text-primary";
    if (!message.user_id || !roomUsers.length) return "text-muted-foreground";

    const userIndex = roomUsers.findIndex(roomUser => roomUser.user_id === message.user_id);
    if (userIndex === -1) return "text-muted-foreground";

    const textColors = [
      "text-blue-500",
      "text-green-500",
      "text-purple-500",
      "text-orange-500",
      "text-pink-500",
      "text-indigo-500",
      "text-teal-500",
      "text-amber-500"
    ];

    return textColors[userIndex % textColors.length];
  };

  // Create display name and avatar letter
  const displayName = user?.nickname || "Unknown User";

  const avatarLetter = generateInitials(user?.nickname);

  // Format timestamp
  const timestamp = typeof message.created_at === 'string'
    ? new Date(message.created_at)
    : new Date(message.created_at);

  // Render personality messages with chat bubble layout (matching user format)
  if (isPersonality) {
    return (
      <div className="mb-4 group">
        <div className="flex gap-2 max-w-4xl justify-start">
          {/* Avatar (bot icon) */}
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <div className="w-8 h-8 rounded-full flex items-center justify-center min-w-[32px] mb-1">
                <Avatar className="w-8 h-8 rounded-md">
                  <AvatarFallback className="bg-lime-300 rounded-md">
                    <Bot className="text-black" size={20} />
                  </AvatarFallback>
                </Avatar>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right">
              {personality.name}
            </TooltipContent>
          </Tooltip>

          {/* Chat Bubble */}
          <div className="relative px-4 py-2 mr-4 rounded-sm break-words bg-zinc-900 text-foreground">
            {/* Personality Name */}
            <div className="text-xs font-semibold mb-1 text-lime-300">
              {personality.name}
            </div>

            {/* Media Items */}
            {'media_items' in message && message.media_items && message.media_items.length > 0 && (
              <MediaItems
                mediaItems={message.media_items}
                className="my-2"
              />
            )}

            {/* Message Content */}
            <div className="prose prose-sm max-w-none break-words">
              <Content content={message.content} />
            </div>

            {/* Timestamp */}
            <div className="flex items-center justify-end mt-2 text-xs text-muted-foreground">
              <FuzzyTimeAgo timestamp={timestamp.getTime()} />
            </div>
          </div>
        </div>
      </div>
    );
  }


  // Render user messages with chat bubble layout (all left-aligned)
  return (
    <div className="mb-4 group">
      <div className="flex gap-2 max-w-4xl justify-start">
        {/* Avatar (always on left side) */}
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center min-w-[32px] mb-1",
            )}>
              <Avatar className="w-8 h-8 rounded-md">
                 {user?.picture && (
                  <AvatarImage src={user.picture} alt={displayName} />
                )}
                <AvatarFallback className={cn(
                  "text-xs font-medium",
                  getUserColor()
                )}>
                  {avatarLetter}
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
            : "bg-zinc-900 text-foreground"
        )}>
          {/* Username */}
          {!isCurrentUser && (
            <div className={cn(
              "text-xs font-semibold mb-1",
              getUsernameColor()
            )}>
              {displayName}
            </div>
          )}

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
            "flex items-center justify-end mt-1 text-xs gap-2",
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

          {/* Media Items */}
          {'media_items' in message && message.media_items && message.media_items.length > 0 && (
            <MediaItems
              mediaItems={message.media_items}
              className="mt-2"
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default PersonalityChatItem;
