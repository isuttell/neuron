import { useEffect } from "react";
import { useSelector } from "react-redux";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { getBuildHashMismatch } from "../slices/appSlice";


export function AppUpdateNotification() {
  const buildHashMismatch = useSelector(getBuildHashMismatch);

  useEffect(() => {
    if (buildHashMismatch) {
      // Schedule auto-reload in 1 hour
      const autoReloadTimer = setTimeout(() => {
        window.location.reload();
      }, 60 * 60 * 1000); // 1 hour in milliseconds

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

      // Cleanup on unmount
      return () => {
        clearTimeout(autoReloadTimer);
      };
    }
  }, [buildHashMismatch]);


  return null; // This component only manages toasts
}
