import { useEffect, useState } from "react";
import { useAppSelector } from "@/hooks";
import { getThreads } from "@/slices/threadsSlice";
import { Spinner } from "./ui/spinner";

export function ThreadsUpdating() {
  const threads = useAppSelector(getThreads);
  const [isUpdating, setIsUpdating] = useState(true);

  useEffect(() => {
    const hasActiveThreads = threads.some((thread) => {
      const lastHour = Date.now() - 60 * 60 * 1000;
      const lastUpdated = new Date(thread.updated_at).getTime();
      return thread.status !== "idle" && lastUpdated > lastHour;
    });
    if (hasActiveThreads) {
      setIsUpdating(true);
    } else {
      setIsUpdating(false);
    }
  }, [threads]);

  return isUpdating ? <Spinner className="size-4" /> : null;
}
