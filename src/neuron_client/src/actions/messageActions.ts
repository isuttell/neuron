import { createAsyncThunk } from "@reduxjs/toolkit";
import { getSocket } from "../slices/socketSlice";
import { RootState } from "../store";

export const fetchMessagesByThread = createAsyncThunk(
  "messages/fetchMessagesByThread",
  async (threadId: string, thunkAPI) => {
    try {
      const response = await fetch(`/api/messages/thread/${threadId}`);
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const sendMessage = createAsyncThunk(
  "messages/sendMessage",
  async (
    {
      threadId,
      prompt,
      greeting,
      personalityId,
    }: {
      threadId: string;
      prompt?: string;
      greeting?: string;
      personalityId: string;
    },
    { getState, rejectWithValue }
  ) => {
    const state = getState() as RootState;
    const socket = getSocket(state);

    if (!socket) {
      return rejectWithValue("Socket not connected");
    }

    try {
      socket.sendMessage({
        type: "PostMessage",
        thread_id: threadId,
        prompt,
        greeting,
        personality_id: personalityId,
      });
      return null;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  }
);
