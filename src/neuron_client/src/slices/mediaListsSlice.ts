import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import { api } from "@/lib/api";
import { MediaItem } from "./mediaSlice";
import { PayloadAction } from "@reduxjs/toolkit";

export interface MediaList {
  id: string;
  name: string;
  description: string;
  tags: string[];
  visibility: string;
  shared_with: string[];
  created_at: string;
  updated_at: string;
}

export interface MediaListItem {
  id: string;
  media_list_id: string;
  media_item_id: string;
  index: number;
}

interface MediaListsState {
  lists: MediaList[];
  mediaListItems: MediaListItem[];
  loading: boolean;
  error: string | null;
}

const initialState: MediaListsState = {
  lists: [],
  mediaListItems: [],
  loading: false,
  error: null,
};

export const fetchMediaList = createAsyncThunk(
  "mediaLists/fetchOne",
  async (listId: string) => {
    const response = await api.get(`/media/lists/${listId}`);
    return response;
  }
);

export const fetchMediaLists = createAsyncThunk(
  "mediaLists/fetchAll",
  async () => {
    const response = await api.get("/media/lists");
    return response;
  }
);

interface CreateMediaListPayload {
  name: string;
  description: string;
}

export const createMediaList = createAsyncThunk(
  "mediaLists/createMediaList",
  async (payload: CreateMediaListPayload) => {
    const response = await api.post("/media/lists", payload);
    return response.media_lists[0];
  }
);

interface AddMediaToListPayload {
  listId: string;
  mediaItemId: string;
  index?: number;
}

export const reorderMediaListItems = createAsyncThunk(
  "mediaLists/reorderItems",
  async ({
    listId,
    mediaItemIds,
  }: {
    listId: string;
    mediaItemIds: string[];
  }) => {
    const response = await api.post(`/media/lists/${listId}/reorder`, {
      media_item_ids: mediaItemIds,
    });
    return response;
  }
);

export const addMediaToList = createAsyncThunk(
  "mediaLists/addMedia",
  async (payload: AddMediaToListPayload) => {
    const response = await api.post(`/media/lists/${payload.listId}/media`, {
      media_item_id: payload.mediaItemId,
      index: payload.index,
    });
    return response;
  }
);

interface FetchMediaListsResponse {
  media_lists: MediaList[];
  media_list_items: MediaListItem[];
  media_items: MediaItem[];
}

interface AddMediaToListResponse {
  media_list_items: MediaListItem[];
}

const mediaListsSlice = createSlice({
  name: "mediaLists",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchMediaList.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchMediaList.fulfilled,
        (state, action: PayloadAction<FetchMediaListsResponse>) => {
          state.loading = false;
          action.payload.media_lists.forEach((list) => {
            const existingIndex = state.lists.findIndex(
              (item) => item.id === list.id
            );
            if (existingIndex !== -1) {
              state.lists[existingIndex] = list;
            } else {
              state.lists.push(list);
            }
          });

          // Update media list items
          const updatedItems = new Map(
            action.payload.media_list_items.map((item) => [item.id, item])
          );

          // Remove items for this list that no longer exist and update existing ones
          state.mediaListItems = state.mediaListItems
            .filter(
              (item) =>
                item.media_list_id !== action.payload.media_lists[0].id ||
                updatedItems.has(item.id)
            )
            .map((item) => updatedItems.get(item.id) || item);

          // Add new items
          action.payload.media_list_items.forEach((item) => {
            if (
              !state.mediaListItems.some((existing) => existing.id === item.id)
            ) {
              state.mediaListItems.push(item);
            }
          });
        }
      )
      .addCase(fetchMediaList.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? "Failed to fetch media list";
      })
      .addCase(fetchMediaLists.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchMediaLists.fulfilled,
        (state, action: PayloadAction<FetchMediaListsResponse>) => {
          state.loading = false;
          state.error = null;
          action.payload.media_lists.forEach((list) => {
            const existingIndex = state.lists.findIndex(
              (item) => item.id === list.id
            );
            if (existingIndex !== -1) {
              // state.lists[existingIndex] = list;
            } else {
              state.lists.push(list);
            }
          });
          // Update or add media list items
          const updatedItems = new Map(
            action.payload.media_list_items.map((item) => [item.id, item])
          );

          // Remove items that no longer exist and update existing ones
          state.mediaListItems = state.mediaListItems
            .filter((item) => updatedItems.has(item.id))
            .map((item) => updatedItems.get(item.id) || item);

          // Add new items
          action.payload.media_list_items.forEach((item) => {
            if (
              !state.mediaListItems.some((existing) => existing.id === item.id)
            ) {
              state.mediaListItems.push(item);
            }
          });
        }
      )
      .addCase(fetchMediaLists.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? "Failed to fetch media lists";
      })
      .addCase(createMediaList.fulfilled, (state, action) => {
        state.lists.push(action.payload);
      })
      .addCase(
        addMediaToList.fulfilled,
        (state, action: PayloadAction<AddMediaToListResponse>) => {
          state.mediaListItems.push(...action.payload.media_list_items);
        }
      )
      .addCase(
        reorderMediaListItems.fulfilled,
        (
          state,
          action: PayloadAction<{ media_list_items: MediaListItem[] }>
        ) => {
          // Update indices of reordered items
          const updatedItems = new Map(
            action.payload.media_list_items.map((item) => [item.id, item])
          );

          state.mediaListItems = state.mediaListItems.map((item) =>
            updatedItems.has(item.id) ? updatedItems.get(item.id)! : item
          );
        }
      );
  },
});

export const {} = mediaListsSlice.actions;

// Selectors
export const selectAllMediaLists = (state: RootState) => state.mediaLists.lists;
export const selectMediaListsLoading = (state: RootState) =>
  state.mediaLists.loading;
export const selectMediaListsError = (state: RootState) =>
  state.mediaLists.error;

export const selectMediaItemsForList = (
  state: RootState,
  listId: string
): MediaItem[] =>
  state.mediaLists.mediaListItems
    .filter((item) => item.media_list_id === listId)
    .sort((a, b) => a.index - b.index)
    .map((item) => {
      const m = state.media.items.find(
        (media) => media.id === item.media_item_id
      );
      if (m) {
        return m;
      }
      throw new Error("Media item not found");
    });

export default mediaListsSlice.reducer;
