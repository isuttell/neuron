import { useEffect } from "react";
import { useAppSelector } from "@/hooks";
import { getThreads } from "@/slices/threadsSlice";

export function ThreadTitleUpdater() {
  const threads = useAppSelector(getThreads);

  useEffect(() => {
    const hasActiveThreads = threads.some((thread) => {
      const lastHour = Date.now() - 60 * 60 * 1000;
      const lastUpdated = new Date(thread.updated_at).getTime();
      return thread.status !== "idle" && lastUpdated > lastHour;
    });
    if (hasActiveThreads) {
      document.title = "🔄 Neuron";
    } else {
      document.title = "Neuron";
    }

    return () => {
      document.title = "Neuron";
    };
  }, [threads]);

  return null;
}
