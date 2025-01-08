import { useEffect, useState } from "react";
import { useAppSelector } from "@/hooks";
import { getThreads } from "@/slices/threadsSlice";
import { Spinner } from "./ui/spinner";

export function ThreadsUpdating() {
  const threads = useAppSelector(getThreads);
  const [isUpdating, setIsUpdating] = useState(true);

  useEffect(() => {
    const hasActiveThreads = threads.some((thread) => thread.status !== "idle");
    if (hasActiveThreads) {
      setIsUpdating(true);
    } else {
      setIsUpdating(false);
    }
  }, [threads]);

  return isUpdating ? <Spinner className="size-4" /> : null;
}
