import { cn } from "@/lib/utils";
import { Personality } from "@/types/personality";
import { useEffect, useState, useRef } from "react";

interface PersonalityStatusMessageProps {
  personality: Personality;
  className?: string;
}

/**
 * Displays the current personality status when the personality is not idle.
 * This provides visibility into what the personality is currently doing.
 */
export function PersonalityStatusMessage({ personality, className }: PersonalityStatusMessageProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const previousStatusRef = useRef<string>("");
  const animationRef = useRef<number | null>(null);

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

  const currentStatus = personality && personality.status && personality.status !== "" ? formatStatus(personality.status) : "";

  useEffect(() => {
    // Reset animation when status changes or becomes idle
    if (!personality || personality.status === "") {
      previousStatusRef.current = "";
      setDisplayedText("");
      setCurrentIndex(0);
    } else if (currentStatus !== previousStatusRef.current) {
      previousStatusRef.current = currentStatus;
      setDisplayedText("");
      setCurrentIndex(0);
    }
  }, [currentStatus, personality]);

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

  if (!personality || personality.status === "") {
    return null;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground ml-2 transition-opacity duration-300",
        className
      )}
    >
      <span className="inline-block">
        {displayedText}
        {currentIndex < currentStatus.length && (
          <span className="opacity-0">|</span>
        )}
      </span>
    </div>
  );
}
