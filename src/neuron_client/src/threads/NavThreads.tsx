import { useEffect } from "react";
import { MessageCircle, MessageCircleDashed } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAppSelector } from "../hooks";
import { useAppDispatch } from "../hooks";
import NewThreadButton from "../threads/NewThreadButton";
import { getThreads, upsertThreads } from "../slices/threadsSlice";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import superagent from "superagent";

export default function NavThreads() {
  const threads = useAppSelector(getThreads);
  const dispatch = useAppDispatch();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  useEffect(() => {
    if (!activePersonalityId) {
      return;
    }
    superagent
      .get(`/api/threads/personality/${activePersonalityId}`)
      .then(({ body }) => {
        dispatch(upsertThreads(body));
      });
  }, [activePersonalityId]);

  return (
    <nav className="grid items-start px-4 mt-2 text-sm font-medium">
      <NewThreadButton />
      {threads
        .filter((thread) => thread.personality_id === activePersonalityId)
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
