import { useAppDispatch, useAppSelector } from "@/hooks";
import { toast } from "sonner";
import { useParams } from "react-router-dom";
import { postMessageByThread, cancelThreadMessages } from "../actions/messageActions";
import { Thread } from "../types/thread";
import MessageForm from "./MessageForm";
import { ThreadStatusMessage } from "@/components/ThreadStatusMessage";
import { cn } from "@/lib/utils";
import { getConnectionStatus } from "@/slices/socketSlice";

/**
 * Props for the ThreadMessageForm component - a business logic wrapper for thread-specific messaging
 */
interface ThreadMessageFormProps {
  /** The thread object containing thread metadata and status */
  thread: Thread;
  /** Additional CSS classes to apply to the underlying MessageForm */
  className?: string;
}

/**
 * ThreadMessageForm - A wrapper component that adds thread-specific business logic to MessageForm
 *
 * This component handles:
 * - Redux integration for posting messages to threads
 * - Toast notifications for user feedback
 * - Error handling for failed message submissions
 * - Loading state management based on thread status
 * - File attachment notifications and user feedback
 *
 * It wraps the pure MessageForm component and provides all the necessary
 * business logic for thread-based messaging functionality.
 *
 * @example
 * ```tsx
 * <ThreadMessageForm
 *   thread={currentThread}
 *   className="max-w-[1170px] w-full mx-auto mt-2"
 * />
 * ```
 */
export default function ThreadMessageForm({
  thread,
  className,
}: ThreadMessageFormProps) {
  const dispatch = useAppDispatch();
  const { threadId } = useParams();
  const isConnected = useAppSelector(getConnectionStatus);

  /**
   * Handles message submission by dispatching to Redux store
   *
   * @param value - The message text content
   * @param file - Optional file attachment
   */
  const handleSubmit = (value: string, file?: File | Blob) => {
    if (!threadId || !thread) return;

    dispatch(
      postMessageByThread({
        threadId,
        prompt: value,
        personalityId: thread.personality_id,
        file,
      })
    ).catch((error) => {
      toast.error("Failed to send message", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    });
  };

  /**
   * Handles file addition by showing appropriate toast notification
   *
   * @param file - The file or audio blob that was added
   * @param isRecording - Whether this is an audio recording or file upload
   */
  const handleFileAdd = (file: File | Blob, isRecording: boolean) => {
    toast(isRecording ? "Recording added" : "Attachment added", {
      description: isRecording
        ? "Ready to send with your message"
        : `${file instanceof File ? file.name : "File"} has been added to the message`,
    });
  };

  /**
   * Handles file removal by showing toast notification
   */
  const handleFileRemove = () => {
    toast("Attachment removed");
  };

  /**
   * Handles thread cancellation by dispatching cancel action
   */
  const handleCancel = () => {
    if (!threadId) return;

    dispatch(cancelThreadMessages(threadId))
      .unwrap()
      .then(() => {
        toast.success("Message cancelled");
      })
      .catch((error) => {
        toast.error("Failed to cancel message", {
          description: error || "An unexpected error occurred",
        });
      });
  };

  const isLoading = thread ? thread.status !== "idle" : false;
  const isDisabled = !isConnected || isLoading;

  return (
    <MessageForm
      className={cn("bg-background rounded-md drop-shadow-md p-2", className)}
      onSubmit={handleSubmit}
      onFileAdd={handleFileAdd}
      onFileRemove={handleFileRemove}
      onCancel={handleCancel}
      isLoading={isLoading}
      disabled={isDisabled}
    >
      <ThreadStatusMessage
        thread={thread}
      />
    </MessageForm>
  );
}
