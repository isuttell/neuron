import { useEffect, useState } from "react";
import { MessageCircle, MessageCircleDashed, Bot } from "lucide-react";
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
import { fetchPersonality } from "@/actions/personalityActions";
import { fetchPersonalityRooms } from "@/actions/personalityRoomActions";
import {
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar";
import { selectRecentSidebarItems } from "@/utils/sidebarSelectors";

interface NavThreadsProps {
  activePathname?: string;
}

export default function NavThreads({ activePathname }: NavThreadsProps) {
  const dispatch = useAppDispatch();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activePersonality = useAppSelector(getActivePersonality);
  const sidebarItems = useAppSelector(
    (state) => selectRecentSidebarItems(state, activePersonalityId),
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
      dispatch(fetchThreadsByPersonality({ personalityId: activePersonalityId })),
      dispatch(fetchPersonalityRooms(activePersonalityId)),
    ]).finally(() => {
      setLoading(false);
    });
  }, [activePersonalityId, dispatch]);

  if (!activePersonality) {
    return (
      <SidebarGroup>
        <SidebarGroupLabel>No personality active</SidebarGroupLabel>
      </SidebarGroup>
    );
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>
        {activePersonality.name}
        {sidebarItems.length >= 50 && (
          <span className="text-xs text-muted-foreground/60 ml-2 italic">
            recent
          </span>
        )}
      </SidebarGroupLabel>
      <NewThreadButton />
      <SidebarGroupContent className="space-y-2">
        {loading && sidebarItems.length === 0 && (
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
        {!loading && sidebarItems.length === 0 && (
          <SidebarMenuItem className="text-small text-muted-foreground">
            <SidebarMenuButton>No threads or rooms yet...</SidebarMenuButton>
          </SidebarMenuItem>
        )}
        {sidebarItems.map((item) => {
          if (item.type === "thread") {
            return (
              <SidebarMenuItem key={item.id} className="gap-2 space-y-1">
                <SidebarMenuButton
                  isActive={activePathname === `/thread/${item.id}`}
                  asChild
                >
                  <NavLink to={`/thread/${item.id}`} className="text-gray-300">
                    <Bot className="size-4 min-w-[20px]" />
                    <span>{item.name || "Start conversation"}</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          } else {
            // Room
            return (
              <SidebarMenuItem key={item.id} className="gap-2 space-y-1">
                <SidebarMenuButton
                  isActive={activePathname === `/personality/${item.personality_id}/room/${item.id}`}
                  asChild
                >
                  <NavLink to={`/personality/${item.personality_id}/room/${item.id}`} className="text-gray-300">
                    {item.status === "idle" ? (
                      <MessageCircle className="size-4 min-w-[20px]" />
                    ) : (
                      <MessageCircleDashed className="size-4 min-w-[20px] text-accent" />
                    )}
                    <span>{item.name || "Unnamed room"}</span>
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          }
        })}
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
