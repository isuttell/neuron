import { createAsyncThunk } from "@reduxjs/toolkit";

export const fetchThread = createAsyncThunk(
  "threads/fetchThread",
  async (threadId: string, thunkAPI) => {
    try {
      const response = await fetch(`/neuron/api/threads/${threadId}`);
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const fetchThreadsByPersonality = createAsyncThunk(
  "threads/fetchThreadsByPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      const response = await fetch(
        `/neuron/api/threads/personality/${personalityId}`
      );
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const createThread = createAsyncThunk(
  "threads/createThread",
  async (
    { personalityId, prompt }: { personalityId: string; prompt?: string },
    thunkAPI
  ) => {
    try {
      const response = await fetch(`/neuron/api/threads/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          personality_id: personalityId,
          prompt: prompt,
        }),
      });
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);
interface UpdateThreadPayload {
  id: string;
  name: string;
  context: string;
}

export const updateThread = createAsyncThunk(
  "threads/updateThread",
  async (thread: UpdateThreadPayload, thunkAPI) => {
    try {
      const response = await fetch(`/neuron/api/threads/${thread.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: thread.name, context: thread.context }),
      });
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const deleteThread = createAsyncThunk(
  "threads/deleteThread",
  async (threadId: string, thunkAPI) => {
    try {
      await fetch(`/neuron/api/threads/${threadId}`, {
        method: "DELETE",
      });
      return threadId;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);
