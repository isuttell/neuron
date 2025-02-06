import { createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "@/lib/api";
import { ThreadResponse, ThreadsResponse } from "@/types/thread";

export const fetchThread = createAsyncThunk(
  "threads/fetchThread",
  async (threadId: string, thunkAPI) => {
    try {
      return await api.get<ThreadResponse>(`/threads/${threadId}`);
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const fetchThreadsByPersonality = createAsyncThunk(
  "threads/fetchThreadsByPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      return await api.get<ThreadsResponse>(
        `/threads/personality/${personalityId}`
      );
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const fetchRecentThreads = createAsyncThunk(
  "threads/fetchRecentThreads",
  async (_, thunkAPI) => {
    try {
      return await api.get<ThreadsResponse>(`/threads/recent`);
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
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
      file?: File | Blob;
    },
    thunkAPI
  ) => {
    try {
      const formData = new FormData();
      formData.append("personality_id", personalityId);
      if (file) {
        if (file instanceof File) {
          formData.append("file", file);
        } else {
          // Convert Blob to File with a timestamp-based name
          const audioFile = new File([file], `recording-${Date.now()}.webm`, {
            type: "audio/webm",
          });
          formData.append("file", audioFile);
        }
      }
      if (prompt) {
        formData.append("prompt", prompt);
      }
      if (greeting) {
        formData.append("greeting", "true");
      }
      return await api.post<ThreadResponse>(`/threads/`, formData);
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
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
      return await api.put<ThreadResponse>(`/threads/${thread.id}`, {
        name: thread.name,
        context: thread.context,
      });
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const deleteThread = createAsyncThunk(
  "threads/deleteThread",
  async (threadId: string, thunkAPI) => {
    try {
      await api.delete(`/threads/${threadId}`);
      return threadId;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
