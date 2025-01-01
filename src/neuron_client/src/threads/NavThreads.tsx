import { useEffect, useState } from "react";
import { MessageCircle, MessageCircleDashed } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAppSelector, useAppDispatch } from "../hooks";
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
import {
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar";

const selectThreads = (state: RootState, personalityId?: string) =>
  state.threads.threads.filter(
    (thread) => thread.personality_id === personalityId
  );

interface NavThreadsProps {
  activePathname?: string;
}

export default function NavThreads({ activePathname }: NavThreadsProps) {
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
      <SidebarGroup>
        <SidebarGroupLabel>No personality active</SidebarGroupLabel>
      </SidebarGroup>
    );
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{activePersonality.name}</SidebarGroupLabel>
      <NewThreadButton />
      <SidebarGroupContent className="space-y-2">
        {loading && threads.length === 0 && (
          <SidebarMenuItem>
            <SidebarMenuButton>
              <Skeleton className="h-4 w-[150px]" />
            </SidebarMenuButton>
            <SidebarMenuButton>
              <Skeleton className="h-4 w-[100px]" />
            </SidebarMenuButton>
            <SidebarMenuButton>
              <Skeleton className="h-4 w-[130px]" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        )}
        {!loading && threads.length === 0 && (
          <SidebarMenuItem className="text-small text-muted-foreground">
            <SidebarMenuButton>No threads yet...</SidebarMenuButton>
          </SidebarMenuItem>
        )}
        {threads
          .sort((a, b) => b.updated_at - a.updated_at)
          .map((thread) => (
            <SidebarMenuItem key={thread.id} className="gap-2 space-y-1">
              <SidebarMenuButton
                isActive={activePathname === `/thread/${thread.id}`}
                asChild
              >
                <NavLink to={`/thread/${thread.id}`} className="text-gray-300">
                  {thread.status === "idle" ? (
                    <MessageCircle className="size-4 min-w-[20px]" />
                  ) : (
                    <MessageCircleDashed className="size-4 min-w-[20px] text-accent" />
                  )}
                  <span>{thread.name || "Start conversation"}</span>
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
