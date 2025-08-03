import React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight, Heart, Bot } from "lucide-react";
import { useAppSelector, useAppDispatch } from "@/hooks";
import { getPersonalities } from "@/slices/personalitiesSlice";
import { getFavoritePersonalityIds } from "@/slices/favoritesSlice";
import { getFavoritePersonalitiesCollapsed, setFavoritePersonalitiesCollapsed } from "@/slices/appSlice";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenu,
} from "@/components/ui/sidebar";

const FavoritePersonalities: React.FC<{ className?: string }> = ({ className }) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const personalities = useAppSelector(getPersonalities);
  const favoritePersonalityIds = useAppSelector(getFavoritePersonalityIds);
  const isCollapsed = useAppSelector(getFavoritePersonalitiesCollapsed);

  // Filter personalities to get only favorites
  const favoritePersonalities = personalities.filter(p => favoritePersonalityIds.has(p.id));

  const handleActivatePersonality = (personalityId: string, personalityName: string) => {
    toast(`${personalityName} selected`);
    navigate(`/${personalityId}`);
  };

  const handleToggleCollapsed = () => {
    dispatch(setFavoritePersonalitiesCollapsed(!isCollapsed));
  };

  return (
    <SidebarMenu className={cn(className)}>
      <SidebarMenuItem>
        <SidebarMenuButton
          onClick={handleToggleCollapsed}
          className="text-gray-300"
        >
          <Heart className="h-4 w-4" />
          <span>Favorites</span>
          <div className="flex-1" />
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </SidebarMenuButton>
      </SidebarMenuItem>

      {!isCollapsed && (
        <>
          {favoritePersonalities.length === 0 ? (
            <SidebarMenuItem>
              <SidebarMenuButton className="text-gray-500 cursor-default pl-8">
                <span className="text-sm">No favorite personalities</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ) : (
            favoritePersonalities.map((personality) => (
              <SidebarMenuItem key={personality.id}>
                <SidebarMenuButton
                  onClick={() => handleActivatePersonality(personality.id, personality.name)}
                  className="text-gray-300"
                >
                  <div className="flex-shrink-0">
                    <Bot className="h-4 w-4" />
                  </div>
                  <span className="truncate">{personality.name}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))
          )}
        </>
      )}
    </SidebarMenu>
  );
};

export default FavoritePersonalities;
