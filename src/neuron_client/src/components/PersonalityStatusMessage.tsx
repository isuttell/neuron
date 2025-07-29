import { cn } from "@/lib/utils";
import { Personality } from "@/types/personality";
import { PersonalityRoom } from "@/types/personalityRoom";
import { useEffect, useState, useRef } from "react";

interface PersonalityStatusMessageProps {
  personality: Personality;
  room?: PersonalityRoom;
  className?: string;
}

// Format the status for display
const formatStatus = (status: string): string => {
  // Handle specific status values
  switch (status) {
    case "working":
      return "Working...";
    case "contemplating":
      return "Contemplating...";
    case "error":
      return "An error occurred";
    default:
      // For all other statuses, display as-is since they are already formatted
      return status;
  }
};

/**
 * Displays the current personality status when the personality is not idle.
 * This provides visibility into what the personality is currently doing.
 */
export function PersonalityStatusMessage({ personality, room, className }: PersonalityStatusMessageProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const previousStatusRef = useRef<string>("");
  const animationRef = useRef<number | null>(null);

  // Use room status if available, otherwise fall back to personality status
  const rawStatus = room?.status || personality?.status || "";
  const currentStatus = rawStatus !== "" ? formatStatus(rawStatus) : "";

  useEffect(() => {
    // Reset animation when status changes or becomes idle
    if (rawStatus === "") {
      previousStatusRef.current = "";
      setDisplayedText("");
      setCurrentIndex(0);
    } else if (currentStatus !== previousStatusRef.current) {
      previousStatusRef.current = currentStatus;
      setDisplayedText("");
      setCurrentIndex(0);
    }
  }, [currentStatus, rawStatus]);

  useEffect(() => {
    // Animate text character by character
    if (currentStatus && currentIndex < currentStatus.length) {
      animationRef.current = window.setTimeout(() => {
        setDisplayedText(currentStatus.slice(0, currentIndex + 1));
        setCurrentIndex(currentIndex + 1);
      }, 15); // 15ms delay between characters (faster animation)
    }

    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
  }, [currentIndex, currentStatus]);

  if (!personality || rawStatus === "") {
    return null;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground ml-2 transition-opacity duration-300",
        className
      )}
    >
     <span className={cn(
        "inline-block",
        currentIndex >= currentStatus.length && "text-shine"
      )}>
        {displayedText}
        {currentIndex < currentStatus.length && (
          <span className="opacity-0">|</span>
        )}
      </span>
    </div>
  );
}
