import { cn } from "@/lib/utils";
import { Thread } from "@/types/thread";
import { Loader2 } from "lucide-react";

interface ThreadStatusMessageProps {
  thread: Thread;
  className?: string;
}

/**
 * Displays the current thread status when the thread is not idle.
 * This provides visibility into what the AI is currently doing.
 */
export function ThreadStatusMessage({ thread, className }: ThreadStatusMessageProps) {
  // Only show status when thread is not idle
  if (!thread || thread.status === "idle") {
    return null;
  }

  // Format the status for display
  const formatStatus = (status: string): string => {
    // Handle specific status values
    switch (status) {
      case "thinking":
        return "Thinking...";
      case "streaming":
        return "Generating response...";
      case "error":
        return "An error occurred";
      default:
        // For all other statuses, display as-is since the status agent
        // generates intelligent messages
        return status;
    }
  };

  return (
    <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", className)}>
      <Loader2 className="h-3 w-3 animate-spin" />
      <span>{formatStatus(thread.status)}</span>
    </div>
  );
}
