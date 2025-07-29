import { createSelector } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import type { Thread } from "../types/thread";
import type { PersonalityRoom } from "../types/personalityRoom";

// Union type for sidebar items
export type SidebarThread = Thread & { type: "thread" };
export type SidebarRoom = PersonalityRoom & { type: "room" };
export type SidebarItem = SidebarThread | SidebarRoom;

// Get threads for a personality
const selectThreadsByPersonality = (state: RootState, personalityId?: string) =>
  state.threads.threads
    .filter((thread) => thread.personality_id === personalityId)
    .map((thread): SidebarThread => ({ ...thread, type: "thread" }));

// Get rooms for a personality
const selectRoomsByPersonality = (state: RootState, personalityId?: string) =>
  state.personalityRoom.roomIds
    .map(id => state.personalityRoom.roomMap[id])
    .filter(room => room && (personalityId ? room.personality_id === personalityId : true))
    .map((room): SidebarRoom => ({ ...room, type: "room" }));

// Combined selector for recent threads and rooms
export const selectRecentSidebarItems = createSelector(
  [selectThreadsByPersonality, selectRoomsByPersonality],
  (threads, rooms): SidebarItem[] => {
    // Combine threads and rooms
    const allItems = [...threads, ...rooms];

    // Sort by updated_at descending (most recent first)
    allItems.sort((a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );

    // Return top 50 most recent items
    return allItems.slice(0, 50);
  }
);
