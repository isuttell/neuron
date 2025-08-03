import { useEffect, useState } from "react";
import { MessageCircle, MessageCircleDashed, Bot } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAppSelector, useAppDispatch } from "../hooks";
import NewThreadButton from "../threads/NewThreadButton";
import { shallowEqual } from "react-redux";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchRecentCombinedItems } from "../actions/threadActions";
import {
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar";
import { selectAllRecentSidebarItemsWithPersonality } from "@/utils/sidebarSelectors";

interface NavThreadsProps {
  activePathname?: string;
}

export default function NavThreads({ activePathname }: NavThreadsProps) {
  const dispatch = useAppDispatch();
  const sidebarItems = useAppSelector(
    selectAllRecentSidebarItemsWithPersonality,
    shallowEqual
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    dispatch(fetchRecentCombinedItems({}))
      .finally(() => {
        setLoading(false);
      });
  }, [dispatch]);

  return (
    <SidebarGroup>
      <SidebarGroupLabel>
        Recent Activity
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
                  <NavLink to={`/thread/${item.id}`} className="text-gray-300 flex items-center gap-2 min-w-0 w-full">
                    <Bot className="size-4 min-w-[20px] flex-shrink-0" />
                    <span className="truncate min-w-0 flex-1">{item.name || "Start conversation"}</span>
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
                  <NavLink to={`/personality/${item.personality_id}/room/${item.id}`} className="text-gray-300 flex items-center gap-2 min-w-0 w-full">
                    {!item.status || item.status === "" || item.status === "contemplating" ? (
                      <MessageCircle className="size-4 min-w-[20px] flex-shrink-0" />
                    ) : (
                      <MessageCircleDashed className="size-4 min-w-[20px] text-accent flex-shrink-0" />
                    )}
                    <span className="truncate min-w-0 flex-1">{item.name || "Unnamed room"}</span>
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
