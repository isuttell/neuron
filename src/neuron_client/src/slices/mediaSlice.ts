import { createSlice, createAsyncThunk, createSelector, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import { api } from "@/lib/api";
import { fetchMessagesByThread } from "@/actions/messageActions";
import { fetchMediaLists } from "./mediaListsSlice";
import {
  fetchPersonalityMessages,
  loadMorePersonalityMessages,
  sendPersonalityMessage
} from "@/actions/personalityChatActions";
import { MediaItem, IncomingMediaEvent } from "@/types/media";

interface MediaState {
  items: MediaItem[];
  loading: boolean;
  error: string | null;
}

const initialState: MediaState = {
  items: [],
  loading: false,
  error: null,
};

interface MediaResponse {
  media_items: MediaItem[];
}

export const fetchRecentMedia = createAsyncThunk(
  "media/fetchRecent",
  async (params: { limit?: number; offset?: number } = {}) => {
    const response = await api.get<MediaResponse>(
      `/media/recent?limit=${params.limit ?? 20}&offset=${params.offset ?? 0}`
    );
    return response.media_items;
  }
);

function upsert(state: MediaState, media: MediaItem) {
  const existingItemIndex = state.items.findIndex(
    (item) => item.id === media.id
  );
  if (existingItemIndex !== -1) {
    // state.items[existingItemIndex] = media;
  } else {
    state.items.push(media);
  }
}

const mediaSlice = createSlice({
  name: "media",
  initialState,
  reducers: {
    clearMedia: (state) => {
      state.items = [];
      state.error = null;
    },
    upsertMedia: (state, action: PayloadAction<IncomingMediaEvent>) => {
      for (const media of action.payload.media) {
        upsert(state, media);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchRecentMedia.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecentMedia.fulfilled, (state, action) => {
        state.loading = false;
        // Create a map of existing items by ID
        const existingItems = state.items.reduce((acc, item) => {
          acc[item.id] = item;
          return acc;
        }, {} as Record<string, MediaItem>);

        // Merge new items, overwriting existing ones with updated data
        action.payload.forEach((item: MediaItem) => {
          existingItems[item.id] = item;
        });

        // Convert back to array and sort by created_at descending
        state.items = Object.values(existingItems).sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      })
      .addCase(fetchRecentMedia.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? "Failed to fetch media items";
      })
      .addCase(fetchMessagesByThread.fulfilled, (state, action) => {
        if (action.payload?.media_items) {
          for (const media of action.payload.media_items) {
            upsert(state, media);
          }
        }
      })
      .addCase(fetchMediaLists.fulfilled, (state, action) => {
        for (const media of action.payload.media_items) {
          upsert(state, media);
        }
      })
      .addCase(fetchPersonalityMessages.fulfilled, (state, action) => {
        if (action.payload?.media_items) {
          for (const media of action.payload.media_items) {
            upsert(state, media);
          }
        }
      })
      .addCase(loadMorePersonalityMessages.fulfilled, (state, action) => {
        if (action.payload?.media_items) {
          for (const media of action.payload.media_items) {
            upsert(state, media);
          }
        }
      })
      .addCase(sendPersonalityMessage.fulfilled, (state, action) => {
        if (action.payload?.media_items) {
          for (const media of action.payload.media_items) {
            upsert(state, media);
          }
        }
      });
  },
});

// Base selectors
const selectMediaState = (state: RootState) => state.media;
const selectMediaItems = (state: RootState) => state.media.items;

// Memoized selectors
export const selectAllMedia = createSelector(
  [selectMediaItems],
  (items) => [...items].sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
);

export const selectMediaLoading = createSelector(
  [selectMediaState],
  (mediaState) => mediaState.loading
);

export const selectMediaError = createSelector(
  [selectMediaState],
  (mediaState) => mediaState.error
);

export const selectMediaItemById = createSelector(
  [selectMediaItems, (_, id: string) => id],
  (items, id) => items.find((item) => item.id === id)
);

export const filterByIds = createSelector(
  [selectMediaItems, (_, ids: string[]) => ids],
  (items, ids) => items.filter((item) => ids.includes(item.id))
);

export const selectMediaByThreadId = createSelector(
  [selectMediaItems, (_, threadId: string) => threadId],
  (items, threadId) => items
    .filter((item) => item.thread_id === threadId)
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
);

export const selectMediaByRoomId = createSelector(
  [
    selectMediaItems,
    (state: RootState) => state.personalityChat.messageMap,
    (state: RootState) => state.personalityChat.messageMediaItemIds,
    (_, roomId: string) => roomId
  ],
  (mediaItems, messageMap, messageMediaItemIds, roomId) => {
    // Find messages for this room
    const roomMessageIds = Object.keys(messageMap).filter(
      messageId => messageMap[messageId]?.personality_room_id === roomId
    );

    // Find media item IDs linked to those messages
    const mediaItemIds = roomMessageIds.flatMap(
      messageId => messageMediaItemIds[messageId] || []
    );

    // Return media items for those IDs
    return mediaItems
      .filter(item => mediaItemIds.includes(item.id))
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  }
);

export const { clearMedia, upsertMedia } = mediaSlice.actions;
export default mediaSlice.reducer;
