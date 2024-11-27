import { useEffect, useState } from "react";
import { MessageCircle, MessageCircleDashed } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAppSelector } from "../hooks";
import { useAppDispatch } from "../hooks";
import NewThreadButton from "../threads/NewThreadButton";
import { shallowEqual } from "react-redux";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getActivePersonalityId,
  getActivePersonality,
} from "../slices/personalitiesSlice";
import { fetchThreadsByPersonality } from "../actions/threadActions";
import { RootState } from "../store";
import { fetchPersonality } from "@/actions/personalityActions";

const selectThreads = (state: RootState, personalityId?: string) =>
  state.threads.threads.filter(
    (thread) => thread.personality_id === personalityId
  );

export default function NavThreads() {
  const dispatch = useAppDispatch();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const threads = useAppSelector(
    (state) => selectThreads(state, activePersonalityId),
    shallowEqual
  );
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!activePersonalityId) {
      return;
    }
    setLoading(true);
    Promise.all([
      dispatch(fetchPersonality(activePersonalityId)),
      dispatch(fetchThreadsByPersonality(activePersonalityId)),
    ]).finally(() => {
      setLoading(false);
    });
  }, [activePersonalityId]);

  if (!activePersonality) {
    return (
      <nav className="grid items-start px-4 mt-2 text-sm font-medium">
        <div className="text-center text-gray-500">No personality active</div>
      </nav>
    );
  }

  return (
    <nav className="grid items-start px-4 mt-2 text-sm font-medium">
      <NewThreadButton />
      <div className="text-xs  text-gray-400 font-bold pl-10 ml-1 mb-2">
        {activePersonality.name}
      </div>
      {loading && threads.length === 0 && (
        <div className="flex flex-col gap-6 my-2 pl-10">
          <Skeleton className="h-4 w-[150px]" />
          <Skeleton className="h-4 w-[100px]" />
          <Skeleton className="h-4 w-[130px]" />
        </div>
      )}
      {!loading && threads.length === 0 && (
        <div className="text-small text-center text-gray-500 mt-4">
          No threads yet
        </div>
      )}
      {threads
        .sort((a, b) => a.updated_at.localeCompare(b.updated_at))
        .reverse()
        .map((thread) => (
          <NavLink
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 transition-all  hover:text-primary ${
                isActive ? "text-primary bg-muted" : "text-muted-foreground"
              }`
            }
            to={`/thread/${thread.id}`}
            key={thread.id}
          >
            {thread.status === "idle" ? (
              <MessageCircle className="size-4 min-w-[20px]" />
            ) : (
              <MessageCircleDashed className="size-4 min-w-[20px]" />
            )}{" "}
            {thread.name || "Start conversation"}
          </NavLink>
        ))}
    </nav>
  );
}
