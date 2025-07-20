import { useEffect, useRef } from "react";
import { useSelector } from "react-redux";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { getBuildHashMismatch } from "../slices/appSlice";

// Constants
const AUTO_RELOAD_DELAY_MS = 60 * 60 * 1000; // 1 hour


export function AppUpdateNotification() {
  const buildHashMismatch = useSelector(getBuildHashMismatch);
  const autoReloadTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Clear any existing timer to prevent memory leaks
    if (autoReloadTimerRef.current) {
      clearTimeout(autoReloadTimerRef.current);
      autoReloadTimerRef.current = null;
    }

    if (buildHashMismatch) {
      // Schedule auto-reload
      autoReloadTimerRef.current = setTimeout(() => {
        window.location.reload();
      }, AUTO_RELOAD_DELAY_MS);

      // Show persistent toast
      toast.warning("Update Available", {
        description: (
          <div className="flex flex-col gap-2">
            <p>A new version is available.</p>
            <Button
              size="sm"
              onClick={() => window.location.reload()}
              className="w-full"
            >
              Refresh Now
            </Button>
          </div>
        ),
        duration: Infinity,
        closeButton: true,
      });
    }

    // Cleanup on unmount or when effect re-runs
    return () => {
      if (autoReloadTimerRef.current) {
        clearTimeout(autoReloadTimerRef.current);
        autoReloadTimerRef.current = null;
      }
    };
  }, [buildHashMismatch]);


  return null; // This component only manages toasts
}
