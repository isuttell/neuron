import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

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

export const threadsSlice = createSlice({
  name: "threads",
  initialState,
  reducers: {
    upsertThreads: (state, action: PayloadAction<IncomingThreadsEvent>) => {
      for (const thread of action.payload.threads) {
        const existingThreadIndex = state.threads.findIndex(
          (item) => item.id === thread.id
        );
        if (existingThreadIndex !== -1) {
          state.threads[existingThreadIndex] = thread;
        } else {
          state.threads.push(thread);
        }
      }
    },
    upsertThread: (state, action: PayloadAction<IncomingThreadEvent>) => {
      const existingThreadIndex = state.threads.findIndex(
        (thread) => thread.id === action.payload.thread.id
      );
      const thread: Thread = action.payload.thread;
      if (existingThreadIndex !== -1) {
        state.threads[existingThreadIndex] = thread;
      } else {
        state.threads.push(thread);
      }
    },
    deleteThread: (state, action: PayloadAction<string>) => {
      state.threads = state.threads.filter(
        (thread) => thread.id !== action.payload
      );
    },
  },
});

export const { upsertThread, upsertThreads, deleteThread } =
  threadsSlice.actions;

export const getThreads = (state: RootState) => state.threads.threads;

export default threadsSlice.reducer;
