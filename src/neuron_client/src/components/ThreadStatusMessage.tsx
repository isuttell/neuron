import { cn } from "@/lib/utils";
import { Thread } from "@/types/thread";
import { Loader2 } from "lucide-react";
import { useEffect, useState, useRef } from "react";

interface ThreadStatusMessageProps {
  thread: Thread;
  className?: string;
}

/**
 * Displays the current thread status when the thread is not idle.
 * This provides visibility into what the AI is currently doing.
 */
export function ThreadStatusMessage({ thread, className }: ThreadStatusMessageProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const previousStatusRef = useRef<string>("");
  const animationRef = useRef<number | null>(null);

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

  const currentStatus = thread && thread.status !== "idle" ? formatStatus(thread.status) : "";

  useEffect(() => {
    // Reset animation when status changes or becomes idle
    if (!thread || thread.status === "idle") {
      previousStatusRef.current = "";
      setDisplayedText("");
      setCurrentIndex(0);
    } else if (currentStatus !== previousStatusRef.current) {
      previousStatusRef.current = currentStatus;
      setDisplayedText("");
      setCurrentIndex(0);
    }
  }, [currentStatus, thread]);

  useEffect(() => {
    // Animate text character by character
    if (currentStatus && currentIndex < currentStatus.length) {
      animationRef.current = window.setTimeout(() => {
        setDisplayedText(currentStatus.slice(0, currentIndex + 1));
        setCurrentIndex(currentIndex + 1);
      }, 30); // 30ms delay between characters
    }

    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
  }, [currentIndex, currentStatus]);

  // Only show status when thread is not idle
  if (!thread || thread.status === "idle") {
    return null;
  }

  return (
    <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", className)}>
      <Loader2 className="h-3 w-3 animate-spin" />
      <span className="inline-block">
        {displayedText}
        {currentIndex < currentStatus.length && (
          <span className="opacity-0">|</span>
        )}
      </span>
    </div>
  );
}
