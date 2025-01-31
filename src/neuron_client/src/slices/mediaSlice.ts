import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import { getAccessToken } from "../actions/getToken";
import { fetchMessagesByThread } from "@/actions/messageActions";
import { fetchMediaLists } from "./mediaListsSlice";
export interface MediaItem {
  id: string;
  name: string;
  description: string;
  url: string;
  media_type: string;
  thread_id?: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

interface IncomingMediaEvent {
  media: MediaItem[];
}

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

export const fetchRecentMedia = createAsyncThunk(
  "media/fetchRecent",
  async ({
    limit = 20,
    offset = 0,
  }: { limit?: number; offset?: number } = {}) => {
    const accessToken = await getAccessToken();
    const response = await fetch(
      `/api/media/recent?limit=${limit}&offset=${offset}`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );
    if (!response.ok) {
      throw new Error("Failed to fetch media items");
    }
    const data = await response.json();
    return data.media_items;
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
      .addCase(
        fetchMessagesByThread.fulfilled,
        (state, action: PayloadAction<IncomingMediaEvent>) => {
          for (const media of action.payload.media) {
            upsert(state, media);
          }
        }
      )
      .addCase(fetchMediaLists.fulfilled, (state, action) => {
        for (const media of action.payload.media_items) {
          upsert(state, media);
        }
      });
  },
});

// Selectors
export const selectAllMedia = (state: RootState) => state.media.items;
export const selectMediaLoading = (state: RootState) => state.media.loading;
export const selectMediaError = (state: RootState) => state.media.error;
export const selectMediaItemById = (state: RootState, id: string) =>
  state.media.items.find((item) => item.id === id);
export const filterByIds = (state: RootState, ids: string[]) =>
  state.media.items.filter((item) => ids.includes(item.id));
export const { clearMedia, upsertMedia } = mediaSlice.actions;
export default mediaSlice.reducer;
