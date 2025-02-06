import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/threadActions";
import * as messageActions from "../actions/messageActions";
import { Thread } from "@/types/thread";

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
              upsert(state, thread);
            }
          }
        }
      );
  },
});

export const { upsertThread, upsertThreads, deleteThread, reset } =
  threadsSlice.actions;
export const selectThread = (state: RootState, threadId?: string) =>
  state.threads.threads.find((thread) => thread.id === threadId);
export const getThreads = (state: RootState) => state.threads.threads;
export const getThreadsLoading = (state: RootState) => state.threads.loading;
export const getThreadsError = (state: RootState) => state.threads.error;

export default threadsSlice.reducer;
