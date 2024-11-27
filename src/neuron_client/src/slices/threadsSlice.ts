import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/threadActions";
export interface Thread {
  id: string;
  name: string;
  context: string;
  memory: string;
  personality_id: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface IncomingThreadEvent {
  thread: Thread;
}

interface IncomingThreadsEvent {
  threads: Thread[];
}

// Define a type for the slice state
interface ThreadState {
  threads: Thread[];
}

// Define the initial state using that type
const initialState: ThreadState = {
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
  },
  extraReducers: (builder) => {
    builder
      .addCase(
        actions.fetchThread.fulfilled,
        (state, action: PayloadAction<IncomingThreadEvent>) => {
          upsert(state, action.payload.thread);
        }
      )
      .addCase(
        actions.fetchThreadsByPersonality.fulfilled,
        (state, action: PayloadAction<IncomingThreadsEvent>) => {
          for (const thread of action.payload.threads) {
            upsert(state, thread);
          }
        }
      )
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
      );
  },
});

export const { upsertThread, upsertThreads, deleteThread } =
  threadsSlice.actions;

export const getThreads = (state: RootState) => state.threads.threads;

export default threadsSlice.reducer;
