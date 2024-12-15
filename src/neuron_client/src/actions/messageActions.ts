import { createAsyncThunk } from "@reduxjs/toolkit";

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
