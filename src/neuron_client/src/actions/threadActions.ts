import { createAsyncThunk } from "@reduxjs/toolkit";

export const fetchThread = createAsyncThunk(
  "threads/fetchThread",
  async (threadId: string, thunkAPI) => {
    try {
      const response = await fetch(`/api/threads/${threadId}`);
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
      const response = await fetch(`/api/threads/personality/${personalityId}`);
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
    {
      personalityId,
      prompt,
      greeting,
      file,
    }: {
      personalityId: string;
      prompt?: string;
      greeting?: boolean;
      file?: File;
    },
    thunkAPI
  ) => {
    try {
      const formData = new FormData();
      formData.append("personality_id", personalityId);
      if (file) {
        formData.append("file", file);
      }
      if (prompt) {
        formData.append("prompt", prompt);
      }
      if (greeting) {
        formData.append("greeting", "true");
      }
      const response = await fetch(`/api/threads/`, {
        method: "POST",
        body: formData,
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
      const response = await fetch(`/api/threads/${thread.id}`, {
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
      await fetch(`/api/threads/${threadId}`, {
        method: "DELETE",
      });
      return threadId;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);
