import { Thread, ThreadUser } from "@/types/thread";
import type { PayloadAction } from "@reduxjs/toolkit";
import { createSelector, createSlice } from "@reduxjs/toolkit";
import * as messageActions from "../actions/messageActions";
import * as actions from "../actions/threadActions";
import type { RootState } from "../store";

interface ThreadUserResponse {
  thread_user: ThreadUser;
}

interface ThreadState {
  loading: boolean;
  error: string | null;
  threads: Thread[];
}

interface IncomingThreadEvent {
  thread: Thread;
}

interface IncomingThreadsEvent {
  threads: Thread[];
}

const initialState: ThreadState = {
  loading: false,
  error: null,
  threads: [],
};
function upsert(state: ThreadState, thread: Thread) {
  const existingThreadIndex = state.threads.findIndex(
    (item) => item.id === thread.id
  );
  if (existingThreadIndex !== -1) {
    state.threads[existingThreadIndex] = thread;
  } else {
    state.threads.push(thread);
  }
}

export const threadsSlice = createSlice({
  name: "threads",
  initialState,
  reducers: {
    upsertThreads: (state, action: PayloadAction<IncomingThreadsEvent>) => {
      for (const thread of action.payload.threads) {
        upsert(state, thread);
      }
    },
    upsertThread: (state, action: PayloadAction<IncomingThreadEvent>) => {
      upsert(state, action.payload.thread);
    },
    deleteThread: (state, action: PayloadAction<string>) => {
      state.threads = state.threads.filter(
        (thread) => thread.id !== action.payload
      );
    },
    reset: (state) => {
      state.loading = false;
      state.error = null;
      state.threads = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(actions.fetchThread.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        actions.fetchThread.fulfilled,
        (state, action: PayloadAction<IncomingThreadEvent>) => {
          upsert(state, action.payload.thread);
          state.loading = false;
          state.error = null;
        }
      )
      .addCase(actions.fetchThread.rejected, (state, action) => {
        state.loading = false;
        state.error = (action.payload as string) || "Failed to fetch thread";
      })
      .addCase(actions.fetchThreadsByPersonality.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        actions.fetchThreadsByPersonality.fulfilled,
        (state, action: PayloadAction<IncomingThreadsEvent>) => {
          for (const thread of action.payload.threads) {
            upsert(state, thread);
          }
          state.loading = false;
          state.error = null;
        }
      )
      .addCase(actions.fetchThreadsByPersonality.rejected, (state, action) => {
        state.loading = false;
        state.error = (action.payload as string) || "Failed to fetch threads";
      })
      .addCase(
        actions.createThread.fulfilled,
        (state, action: PayloadAction<IncomingThreadEvent>) => {
          upsert(state, action.payload.thread);
        }
      )
      .addCase(
        actions.updateThread.fulfilled,
        (state, action: PayloadAction<IncomingThreadEvent>) => {
          upsert(state, action.payload.thread);
        }
      )
      .addCase(
        actions.deleteThread.fulfilled,
        (state, action: PayloadAction<string>) => {
          state.threads = state.threads.filter(
            (thread) => thread.id !== action.payload
          );
        }
      )
      .addCase(
        actions.fetchRecentThreads.fulfilled,
        (state, action: PayloadAction<IncomingThreadsEvent>) => {
          for (const thread of action.payload.threads) {
            upsert(state, thread);
          }
        }
      )
      .addCase(
        messageActions.fetchMessagesByThread.fulfilled,
        (state, action) => {
          if (action.payload?.threads) {
            for (const thread of action.payload.threads) {
              // Create a copy of the thread to add thread_users if available
              const threadWithUsers = { ...thread };

              // If thread_users are available in the payload, add them to the thread
              if (action.payload.thread_users) {
                const threadUsers = action.payload.thread_users.filter(
                  (tu: { thread_id: string; user_id: string; role: string }) =>
                    tu.thread_id === thread.id
                );
                if (threadUsers.length > 0) {
                  threadWithUsers.thread_users = threadUsers;
                }
              }

              upsert(state, threadWithUsers);
            }
          }
        }
      )
      .addCase(actions.addUserByEmail.fulfilled, (state, action) => {
        // Use unknown as an intermediate type for safer type casting
        const payload = action.payload as unknown;

        // Type guard to check if payload has the expected structure
        const isThreadUserResponse = (
          obj: unknown
        ): obj is ThreadUserResponse => {
          return (
            obj !== null &&
            typeof obj === "object" &&
            "thread_user" in obj &&
            obj.thread_user !== null &&
            typeof obj.thread_user === "object" &&
            "thread_id" in obj.thread_user
          );
        };

        if (isThreadUserResponse(payload)) {
          const threadId = payload.thread_user.thread_id;
          const threadIndex = state.threads.findIndex((t) => t.id === threadId);

          if (threadIndex !== -1) {
            const thread = state.threads[threadIndex];
            // Create a new thread_users array if it doesn't exist
            const threadUsers = thread.thread_users || [];
            // Add the new thread user
            const updatedThreadUsers = [...threadUsers, payload.thread_user];
            // Update the thread with the new thread_users array
            state.threads[threadIndex] = {
              ...thread,
              thread_users: updatedThreadUsers,
            };
          }
        }
      });
  },
});

export const { upsertThread, upsertThreads, deleteThread, reset } =
  threadsSlice.actions;
// Basic selectors
export const getThreadsState = (state: RootState) => state.threads.threads;
export const getThreadsLoadingState = (state: RootState) => state.threads.loading;
export const getThreadsErrorState = (state: RootState) => state.threads.error;

// Memoized selectors with transformations to avoid identity function warnings
export const getThreads = createSelector(
  [getThreadsState],
  (threads) => [...threads] // Create a new array to avoid identity function warning
);

export const getThreadsLoading = createSelector(
  [getThreadsLoadingState],
  (loading) => loading === true // Convert to boolean to avoid identity function warning
);

export const getThreadsError = createSelector(
  [getThreadsErrorState],
  (error) => error === null ? null : error // Apply conditional to avoid identity function warning
);

export const selectThread = createSelector(
  [getThreadsState, (_state: RootState, threadId?: string) => threadId],
  (threads, threadId) => threads.find((thread) => thread.id === threadId)
);

export const getThreadUsers = createSelector(
  [getThreadsState, (_state: RootState, threadId: string) => threadId],
  (threads, threadId) => {
    const thread = threads.find((t) => t.id === threadId);
    return thread?.thread_users || [];
  }
);

export default threadsSlice.reducer;
