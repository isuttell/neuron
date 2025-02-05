import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/threadActions";
import * as messageActions from "../actions/messageActions";
export interface Thread {
  id: string;
  name: string;
  context: string;
  memory: string;
  personality_id: string;
  status: string;
  message_count: number;
  created_at: number;
  updated_at: number;
}

interface IncomingThread extends Omit<Thread, "created_at" | "updated_at"> {
  created_at: string;
  updated_at: string;
}

interface IncomingThreadEvent {
  thread: IncomingThread;
}

interface IncomingThreadsEvent {
  threads: IncomingThread[];
}

// Define a type for the slice state
interface ThreadState {
  loading: boolean;
  error: string | null;
  threads: Thread[];
}

// Define the initial state using that type
const initialState: ThreadState = {
  loading: false,
  error: null,
  threads: [],
};
/**
 * Parses an incoming message dates and returns a Message object
 * @param message - The incoming message
 * @returns A Message object
 */
function parseIncomingThread(thread: IncomingThread): Thread {
  return {
    ...thread,
    created_at: new Date(thread.created_at).getTime(),
    updated_at: new Date(thread.updated_at).getTime(),
  };
}

function upsert(state: ThreadState, incomingThread: IncomingThread) {
  const thread = parseIncomingThread(incomingThread);
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
        (state, action: PayloadAction<IncomingThreadsEvent>) => {
          for (const thread of action.payload.threads) {
            upsert(state, thread);
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
