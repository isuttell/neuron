import { configureStore, Store } from "@reduxjs/toolkit";
import mediaListsReducer, {
  MediaList,
  MediaListItem,
  fetchMediaList,
  fetchMediaLists,
  createMediaList,
  addMediaToList,
  reorderMediaListItems,
  selectAllMediaLists,
  selectMediaListsLoading,
  selectMediaListsError,
  selectMediaItemsForList
} from "../mediaListsSlice";
import { MediaItem } from "@/types/media";
import type { RootState } from "../../store";

describe("mediaListsSlice", () => {
  let store: Store<{
    mediaLists: ReturnType<typeof mediaListsReducer>;
    media: { items: MediaItem[] };
  }>;

  // Mock data
  const mockMediaList: MediaList = {
    id: "list-1",
    name: "Test List",
    description: "A test media list",
    tags: ["test", "media"],
    visibility: "private",
    shared_with: [],
    created_at: "2024-02-04T12:00:00Z",
    updated_at: "2024-02-04T12:00:00Z"
  };

  const mockMediaListItem: MediaListItem = {
    id: "list-item-1",
    media_list_id: "list-1",
    media_item_id: "media-1",
    index: 0
  };

  const mockMediaItem: MediaItem = {
    id: "media-1",
    name: "Test Media",
    description: "A test media item",
    url: "https://example.com/test.mp4",
    media_type: "video",
    user_id: "user-1",
    created_at: "2024-02-04T12:00:00Z",
    updated_at: "2024-02-04T12:00:00Z"
  };

  beforeEach(() => {
    // Create a properly typed media reducer
    const mediaReducer = (
      state: { items: MediaItem[] } = { items: [mockMediaItem] }
    ): { items: MediaItem[] } => state;

    store = configureStore({
      reducer: {
        mediaLists: mediaListsReducer,
        media: mediaReducer
      }
    });
  });

  describe("initial state", () => {
    it("should have empty lists", () => {
      const state = store.getState().mediaLists;
      expect(state.lists).toEqual([]);
    });

    it("should have empty mediaListItems array", () => {
      const state = store.getState().mediaLists;
      expect(state.mediaListItems).toEqual([]);
    });

    it("should have loading set to false", () => {
      const state = store.getState().mediaLists;
      expect(state.loading).toBe(false);
    });

    it("should have error set to null", () => {
      const state = store.getState().mediaLists;
      expect(state.error).toBeNull();
    });
  });

  describe("async thunks", () => {
    describe("fetchMediaList", () => {
      it("should set loading true when pending", () => {
        store.dispatch(fetchMediaList.pending("", "list-1"));
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(true);
        expect(state.error).toBeNull();
      });

      it("should update state when fulfilled", () => {
        store.dispatch(
          fetchMediaList.fulfilled(
            {
              media_lists: [mockMediaList],
              media_list_items: [mockMediaListItem],
              media_items: [mockMediaItem]
            },
            "",
            "list-1"
          )
        );
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(false);
        expect(state.lists).toContainEqual(mockMediaList);
        expect(state.mediaListItems).toContainEqual(mockMediaListItem);
      });

      it("should set error when rejected", () => {
        store.dispatch(
          fetchMediaList.rejected(new Error("Failed to fetch"), "", "list-1")
        );
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(false);
        expect(state.error).toBe("Failed to fetch");
      });

      it("should set default error when rejected without message", () => {
        store.dispatch(fetchMediaList.rejected(new Error(), "", "list-1"));
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(false);
        expect(state.error).toBe("");
      });
    });

    describe("fetchMediaLists", () => {
      it("should set loading true when pending", () => {
        store.dispatch(fetchMediaLists.pending(""));
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(true);
        expect(state.error).toBeNull();
      });

      it("should update state when fulfilled", () => {
        const secondMediaList = { ...mockMediaList, id: "list-2", name: "Second List" };
        const secondMediaListItem = { ...mockMediaListItem, id: "list-item-2", media_list_id: "list-2" };

        store.dispatch(
          fetchMediaLists.fulfilled(
            {
              media_lists: [mockMediaList, secondMediaList],
              media_list_items: [mockMediaListItem, secondMediaListItem],
              media_items: [mockMediaItem]
            },
            ""
          )
        );
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(false);
        expect(state.error).toBeNull();
        expect(state.lists).toHaveLength(2);
        expect(state.mediaListItems).toHaveLength(2);
      });

      it("should set error when rejected", () => {
        store.dispatch(
          fetchMediaLists.rejected(new Error("Failed to fetch"), "")
        );
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(false);
        expect(state.error).toBe("Failed to fetch");
      });

      it("should set default error when rejected without message", () => {
        store.dispatch(fetchMediaLists.rejected(new Error(), ""));
        const state = store.getState().mediaLists;
        expect(state.loading).toBe(false);
        expect(state.error).toBe("");
      });
    });

    describe("createMediaList", () => {
      it("should add new list when fulfilled", () => {
        store.dispatch(
          createMediaList.fulfilled(
            mockMediaList,
            "",
            { name: "Test List", description: "A test media list" }
          )
        );
        const state = store.getState().mediaLists;
        expect(state.lists).toContainEqual(mockMediaList);
      });
    });

    describe("addMediaToList", () => {
      it("should add media list item when fulfilled", () => {
        store.dispatch(
          addMediaToList.fulfilled(
            { media_list_items: [mockMediaListItem] },
            "",
            { listId: "list-1", mediaItemId: "media-1", index: 0 }
          )
        );
        const state = store.getState().mediaLists;
        expect(state.mediaListItems).toContainEqual(mockMediaListItem);
      });
    });

    describe("reorderMediaListItems", () => {
      it("should update media list items when fulfilled", () => {
        // First add an item
        store.dispatch(
          addMediaToList.fulfilled(
            { media_list_items: [mockMediaListItem] },
            "",
            { listId: "list-1", mediaItemId: "media-1", index: 0 }
          )
        );

        // Then add another item
        const secondItem = { ...mockMediaListItem, id: "list-item-2", media_item_id: "media-2", index: 1 };
        store.dispatch(
          addMediaToList.fulfilled(
            { media_list_items: [secondItem] },
            "",
            { listId: "list-1", mediaItemId: "media-2", index: 1 }
          )
        );

        // Then reorder them
        const reorderedItems = [
          { ...mockMediaListItem, index: 1 },
          { ...secondItem, index: 0 }
        ];

        store.dispatch(
          reorderMediaListItems.fulfilled(
            { media_list_items: reorderedItems },
            "",
            { listId: "list-1", mediaItemIds: ["media-2", "media-1"] }
          )
        );

        const state = store.getState().mediaLists;
        expect(state.mediaListItems).toHaveLength(2);
        expect(state.mediaListItems.find(item => item.id === "list-item-1")?.index).toBe(1);
        expect(state.mediaListItems.find(item => item.id === "list-item-2")?.index).toBe(0);
      });
    });
  });

  describe("selectors", () => {
    beforeEach(() => {
      // Set up initial state with some data
      store.dispatch(
        fetchMediaLists.fulfilled(
          {
            media_lists: [mockMediaList],
            media_list_items: [mockMediaListItem],
            media_items: [mockMediaItem]
          },
          ""
        )
      );
    });

    it("should select all media lists sorted by updated_at", () => {
      const newerList = {
        ...mockMediaList,
        id: "list-2",
        name: "Newer List",
        updated_at: "2024-02-05T12:00:00Z"
      };

      store.dispatch(
        createMediaList.fulfilled(
          newerList,
          "",
          { name: "Newer List", description: "A newer test media list" }
        )
      );

      const lists = selectAllMediaLists(store.getState() as RootState);
      expect(lists).toHaveLength(2);
      expect(lists[0].id).toBe("list-2"); // Newer list should be first
      expect(lists[1].id).toBe("list-1");
    });

    it("should select media items for a specific list", () => {
      const mediaItems = selectMediaItemsForList(
        store.getState() as RootState,
        "list-1"
      );
      expect(mediaItems).toHaveLength(1);
      expect(mediaItems[0].id).toBe("media-1");
    });

    it("should throw error when media item is not found", () => {
      // Create a list item referencing a non-existent media item
      const invalidListItem = {
        ...mockMediaListItem,
        id: "invalid-item",
        media_item_id: "non-existent"
      };

      store.dispatch(
        addMediaToList.fulfilled(
          { media_list_items: [invalidListItem] },
          "",
          { listId: "list-1", mediaItemId: "non-existent", index: 1 }
        )
      );

      expect(() => {
        selectMediaItemsForList(store.getState() as RootState, "list-1");
      }).toThrow("Media item not found");
    });

    it("should select loading state", () => {
      const loading = selectMediaListsLoading(store.getState() as RootState);
      expect(loading).toBe(false);

      store.dispatch(fetchMediaLists.pending(""));
      const loadingState = selectMediaListsLoading(store.getState() as RootState);
      expect(loadingState).toBe(true);
    });

    it("should select error state", () => {
      const error = selectMediaListsError(store.getState() as RootState);
      expect(error).toBeNull();

      store.dispatch(
        fetchMediaLists.rejected(new Error("Test error"), "")
      );
      const errorState = selectMediaListsError(store.getState() as RootState);
      expect(errorState).toBe("Test error");
    });
  });
});
