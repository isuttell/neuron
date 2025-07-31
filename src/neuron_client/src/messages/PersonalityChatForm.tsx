import { useAppSelector } from "@/hooks";
import { toast } from "sonner";
import MessageForm from "./MessageForm";
import { cn } from "@/lib/utils";
import { getConnectionStatus } from "@/slices/socketSlice";
import { getPersonalityChatLoading } from "@/slices/personalityChatSlice";
import { PersonalityStatusMessage } from "@/components/PersonalityStatusMessage";
import { Personality } from "@/types/personality";
import { PersonalityRoom } from "@/types/personalityRoom";
import { Spinner } from "@/components/ui/spinner";

/**
 * Props for the PersonalityChatForm component - a business logic wrapper for personality chat messaging
 */
interface PersonalityChatFormProps {
  /** The personality being chatted with */
  personality: Personality;
  /** The room being chatted in (optional, for room-specific status) */
  room?: PersonalityRoom;
  /** Callback fired when a message should be sent */
  onSendMessage: (content: string, file?: File | Blob) => void;
  /** Additional CSS classes to apply to the underlying MessageForm */
  className?: string;
  /** Message being edited (null if not editing) */
  editingMessage?: { id: string; content: string } | null;
  /** Callback fired when editing should be cancelled */
  onCancelEdit?: () => void;
  /** Whether the user is subscribed to the personality room */
  isSubscribed?: boolean;
}

/**
 * PersonalityChatForm - A wrapper component that adds personality chat-specific business logic to MessageForm
 *
 * This component handles:
 * - Message submission for personality chat
 * - Toast notifications for user feedback
 * - Loading state management
 * - Connection status checking
 *
 * It wraps the pure MessageForm component and provides all the necessary
 * business logic for personality chat messaging functionality.
 *
 * @example
 * ```tsx
 * <PersonalityChatForm
 *   personality={currentPersonality}
 *   onSendMessage={handleSendMessage}
 *   className="max-w-[1170px] w-full mx-auto mt-2"
 * />
 * ```
 */
export default function PersonalityChatForm({
  personality,
  room,
  onSendMessage,
  className,
  editingMessage,
  onCancelEdit,
  isSubscribed = true,
}: PersonalityChatFormProps) {
  const isConnected = useAppSelector(getConnectionStatus);
  const isLoading = useAppSelector(getPersonalityChatLoading);

  const isEditMode = !!editingMessage;
  // Check room status if available, otherwise fall back to personality status
  const isPersonalityBusy = room ? (room.status ?? "") !== "" : personality.status !== "";

  /**
   * Handles message submission
   *
   * @param value - The message text content
   * @param file - Optional file attachment
   */
  const handleSubmit = (value: string, file?: File | Blob) => {
    if (!value.trim() && !file) return;

    try {
      onSendMessage(value.trim(), file);
    } catch (error) {
      toast.error("Failed to send message", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
  };

  /**
   * Handles file removal
   */
  const handleFileRemove = () => {
    toast("Attachment removed");
  };

  const isDisabled = !isConnected || isLoading || !isSubscribed;

  return (
    <div>
      {/* Edit mode indicator */}
      {isEditMode && (
        <div className="text-sm text-white pl-2 pt-2 mx-auto max-w-3xl">
          Editing message...
        </div>
      )}



      {/* Personality status indicator */}

      <MessageForm
        className={cn("bg-background rounded-md drop-shadow-md p-2", className)}
        onSubmit={handleSubmit}
        onFileRemove={handleFileRemove}
        onCancelEdit={onCancelEdit}
        isLoading={isLoading}
        disabled={isDisabled}
        placeholder={isEditMode ? "Edit your message..." : "Type your message..."}
        initialValue={editingMessage?.content || ""}
        editMode={isEditMode}
        showUpload={true}
        showRecord={true}
        showPrompts={false}
      >
              {/* Subscription status indicator */}
      {!isSubscribed && (
        <div className="flex items-center pl-2 pt-2 mx-auto max-w-3xl">
          <Spinner size={16} className="text-muted-foreground" />
        </div>
      )}
        {isPersonalityBusy && (
          <PersonalityStatusMessage personality={personality} room={room} />
        )}
      </MessageForm>
    </div>
  );
}
