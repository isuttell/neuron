import { createAsyncThunk } from "@reduxjs/toolkit";
import { getSocket } from "../slices/socketSlice";
import { RootState } from "../store";
import { getAccessToken } from "./getToken";

export const fetchMessagesByThread = createAsyncThunk(
  "messages/fetchMessagesByThread",
  async (threadId: string, thunkAPI) => {
    try {
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/messages/thread/${threadId}`, {
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

export const postMessageByThread = createAsyncThunk(
  "messages/postMessageByThread",
  async (
    {
      threadId,
      prompt,
      personalityId,
      file,
    }: {
      threadId: string;
      prompt: string;
      personalityId: string;
      file?: File | Blob;
    },
    thunkAPI
  ) => {
    try {
      const formData = new FormData();
      formData.append("prompt", prompt);
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

      const accessToken = await getAccessToken();
      const response = await fetch(`/api/messages/thread/${threadId}`, {
        method: "POST",
        body: formData,
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      return await response.json();
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
