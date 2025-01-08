import { useEffect } from "react";
import { useAppSelector } from "@/hooks";
import { getThreads } from "@/slices/threadsSlice";

export function ThreadTitleUpdater() {
  const threads = useAppSelector(getThreads);

  useEffect(() => {
    const hasActiveThreads = threads.some((thread) => thread.status !== "idle");

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
