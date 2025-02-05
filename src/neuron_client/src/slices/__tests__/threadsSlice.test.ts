import { configureStore } from "@reduxjs/toolkit";
import threadsReducer, {
  Thread,
  upsertThread,
  upsertThreads,
  deleteThread,
  selectThread,
  getThreads,
  getThreadsLoading,
  getThreadsError,
  reset,
} from "../threadsSlice";
import * as actions from "../../actions/threadActions";
import * as messageActions from "../../actions/messageActions";

describe("threadsSlice", () => {
  const mockThread: Thread = {
    id: "1",
    name: "Test Thread",
    context: "Test Context",
    memory: "Test Memory",
    personality_id: "test-personality",
    status: "active",
    message_count: 0,
    created_at: new Date("2024-02-03T00:00:00Z").getTime(),
    updated_at: new Date("2024-02-03T00:00:00Z").getTime(),
  };

  const mockIncomingThread = {
    ...mockThread,
    created_at: "2024-02-03T00:00:00Z",
    updated_at: "2024-02-03T00:00:00Z",
  };

  const store = configureStore({
    reducer: {
      app: () => ({
        sidebar_image: "",
        isLoading: false,
        error: null,
      }),
      messages: () => ({
        messageMap: {},
        messageIds: [],
        loading: false,
        error: null,
      }),
      threads: threadsReducer,
      socket: () => ({
        connected: false,
        socket: null,
      }),
      personalities: () => ({
        loading: false,
        error: null,
        personalities: [],
      }),
      images: () => ({
        loading: false,
        error: null,
        images: [],
      }),
      prompts: () => ({
        loading: false,
        error: null,
        prompts: {},
      }),
      embeddings: () => ({
        loading: false,
        error: null,
        personality: {},
      }),
      media: () => ({
        loading: false,
        error: null,
        items: [],
      }),
      mediaLists: () => ({
        loading: false,
        error: null,
        lists: [],
        mediaListItems: [],
      }),
      scheduler: () => ({
        loading: false,
        error: null,
        events: [],
      }),
      providers: () => ({
        loading: false,
        error: null,
        providers: {},
        activeProviderId: null,
      }),
    },
  });

  beforeEach(() => {
    store.dispatch(reset());
  });

  describe("initial state", () => {
    it("should have correct initial state", () => {
      const state = store.getState().threads;
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.threads).toEqual([]);
    });
  });

  describe("reducers", () => {
    it("should handle upsertThread", () => {
      store.dispatch(upsertThread({ thread: mockIncomingThread }));
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(1);
      expect(state.threads[0]).toEqual(mockThread);
    });

    it("should update existing thread with upsertThread", () => {
      store.dispatch(upsertThread({ thread: mockIncomingThread }));
      const updatedThread = {
        ...mockIncomingThread,
        name: "Updated Thread",
      };
      store.dispatch(upsertThread({ thread: updatedThread }));
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(1);
      expect(state.threads[0].name).toBe("Updated Thread");
    });

    it("should handle upsertThreads", () => {
      const threads = [mockIncomingThread, { ...mockIncomingThread, id: "2" }];
      store.dispatch(upsertThreads({ threads }));
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(2);
    });

    it("should handle deleteThread", () => {
      store.dispatch(upsertThread({ thread: mockIncomingThread }));
      const state1 = store.getState().threads;
      expect(state1.threads).toHaveLength(1);
      store.dispatch(deleteThread(state1.threads[0].id));
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(0);
    });
  });

  describe("extra reducers", () => {
    it("should handle fetchThread.pending", () => {
      store.dispatch(actions.fetchThread.pending("", "1"));
      const state = store.getState().threads;
      expect(state.loading).toBe(true);
      expect(state.error).toBeNull();
    });

    it("should handle fetchThread.fulfilled", () => {
      store.dispatch(
        actions.fetchThread.fulfilled({ thread: mockIncomingThread }, "", "1")
      );
      const state = store.getState().threads;
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.threads[0]).toEqual(mockThread);
    });

    it("should handle fetchThread.rejected", () => {
      const error = "Error fetching thread";
      store.dispatch(actions.fetchThread.rejected(new Error(), "", "1", error));
      const state = store.getState().threads;
      expect(state.loading).toBe(false);
      expect(state.error).toBe(error);
    });

    it("should handle fetchThreadsByPersonality.fulfilled", () => {
      const threads = [mockIncomingThread, { ...mockIncomingThread, id: "2" }];
      store.dispatch(
        actions.fetchThreadsByPersonality.fulfilled(
          { threads },
          "",
          "test-personality"
        )
      );
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(2);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("should handle createThread.fulfilled", () => {
      store.dispatch(
        actions.createThread.fulfilled({ thread: mockIncomingThread }, "", {
          personalityId: "test-personality",
          prompt: "Test Thread",
        })
      );
      const state = store.getState().threads;
      expect(state.threads[0]).toEqual(mockThread);
    });

    it("should handle updateThread.fulfilled", () => {
      store.dispatch(upsertThread({ thread: mockIncomingThread }));
      const updatedThread = {
        ...mockIncomingThread,
        name: "Updated Thread",
      };
      store.dispatch(
        actions.updateThread.fulfilled({ thread: updatedThread }, "", {
          id: "1",
          name: "Updated Thread",
          context: "Updated Context",
        })
      );
      const state = store.getState().threads;
      expect(state.threads[0].name).toBe("Updated Thread");
    });

    it("should handle deleteThread.fulfilled", () => {
      store.dispatch(upsertThread({ thread: mockIncomingThread }));
      const state1 = store.getState().threads;
      expect(state1.threads).toHaveLength(1);
      store.dispatch(
        actions.deleteThread.fulfilled(
          state1.threads[0].id,
          "",
          state1.threads[0].id
        )
      );
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(0);
    });

    it("should handle fetchRecentThreads.fulfilled", () => {
      const threads = [mockIncomingThread, { ...mockIncomingThread, id: "2" }];
      store.dispatch(
        actions.fetchRecentThreads.fulfilled({ threads }, "", undefined)
      );
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(2);
    });

    it("should handle messageActions.fetchMessagesByThread.fulfilled", () => {
      const threads = [mockIncomingThread];
      store.dispatch(
        messageActions.fetchMessagesByThread.fulfilled({ threads }, "", "1")
      );
      const state = store.getState().threads;
      expect(state.threads).toHaveLength(1);
      expect(state.threads[0]).toEqual(mockThread);
    });
  });

  describe("selectors", () => {
    beforeEach(() => {
      store.dispatch(upsertThread({ thread: mockIncomingThread }));
    });

    it("should select thread by id", () => {
      const thread = selectThread(store.getState(), mockThread.id);
      expect(thread).toEqual(mockThread);
    });

    it("should return undefined for non-existent thread", () => {
      const thread = selectThread(store.getState(), "non-existent");
      expect(thread).toBeUndefined();
    });

    it("should get all threads", () => {
      const threads = getThreads(store.getState());
      expect(threads).toHaveLength(1);
      expect(threads[0]).toEqual(mockThread);
    });

    it("should get loading state", () => {
      const loading = getThreadsLoading(store.getState());
      expect(loading).toBe(false);
    });

    it("should get error state", () => {
      const error = getThreadsError(store.getState());
      expect(error).toBeNull();
    });
  });
});
