import { api } from "@/lib/api";
import { MessageResponse } from "@/types/message";
import { createAsyncThunk } from "@reduxjs/toolkit";
import { getSocket } from "../slices/socketSlice";
import { RootState } from "../store";
import { WebSocketPayload } from "../types/websocket";

export const fetchMessagesByThread = createAsyncThunk(
  "messages/fetchMessagesByThread",
  async (threadId: string, thunkAPI) => {
    try {
      return await api.get<MessageResponse>(`/messages/thread/${threadId}`);
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
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

      return await api.post(`/messages/thread/${threadId}`, formData);
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
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
      } as WebSocketPayload);
      return null;
    } catch (error) {
      if (error instanceof Error) {
        return rejectWithValue(error.message);
      }
      return rejectWithValue("An unknown error occurred");
    }
  }
);
