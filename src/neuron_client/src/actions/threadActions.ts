import { createAsyncThunk } from "@reduxjs/toolkit";
import { getAccessToken } from "./getToken";

export const fetchThread = createAsyncThunk(
  "threads/fetchThread",
  async (threadId: string, thunkAPI) => {
    try {
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/threads/${threadId}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
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
      const accessToken = await getAccessToken();
      const response = await fetch(
        `/api/threads/personality/${personalityId}`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const fetchRecentThreads = createAsyncThunk(
  "threads/fetchRecentThreads",
  async (_, thunkAPI) => {
    try {
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/threads/recent`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/threads/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/threads/${thread.id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${accessToken}`,
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
      const accessToken = await getAccessToken();
      await fetch(`/api/threads/${threadId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      return threadId;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);
