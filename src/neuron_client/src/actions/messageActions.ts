import { api } from "@/lib/api";
import { MessageResponse } from "@/types/message";
import { createAsyncThunk } from "@reduxjs/toolkit";
import {
  addOptimisticMessage,
  markMessageFailed,
  markMessageCancelled,
  getMessages,
} from "../slices/messagesSlice";
import { getConnectionStatus } from "../slices/socketSlice";
import { socketManager } from "../WebSocketManager";
import { RootState } from "../store";
import { WebSocketPayload } from "../types/websocket";
import { toSerializableError, isClassifiedError } from "../types/error";

export const fetchMessagesByThread = createAsyncThunk(
  "messages/fetchMessagesByThread",
  async (threadId: string, thunkAPI) => {
    try {
      return await api.get<MessageResponse>(`/messages/thread/${threadId}`);
    } catch (error) {
      // Convert ClassifiedError to SerializableError for Redux state
      if (isClassifiedError(error)) {
        return thunkAPI.rejectWithValue(toSerializableError(error));
      }
      // Fallback for other error types
      return thunkAPI.rejectWithValue({
        message: error instanceof Error ? error.message : "An unknown error occurred",
        type: "unknown" as const,
      });
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
    // Generate a temporary ID for the optimistic message
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Add optimistic message immediately
    thunkAPI.dispatch(
      addOptimisticMessage({
        tempId,
        content: prompt,
        threadId,
      })
    );

    try {
      const formData = new FormData();
      formData.append("prompt", prompt);
      formData.append("personality_id", personalityId);
      formData.append("temp_id", tempId);

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

      const result = await api.post(`/messages/thread/${threadId}`, formData);
      return result;
    } catch (error) {
      // Mark the optimistic message as failed
      thunkAPI.dispatch(
        markMessageFailed({
          tempId,
          error: error instanceof Error ? error.message : "Failed to send message",
        })
      );

      // Convert ClassifiedError to SerializableError for Redux state
      if (isClassifiedError(error)) {
        return thunkAPI.rejectWithValue(toSerializableError(error));
      }
      // Fallback for other error types
      return thunkAPI.rejectWithValue({
        message: error instanceof Error ? error.message : "An unknown error occurred",
        type: "unknown" as const,
      });
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
    const connected = getConnectionStatus(state);

    if (!connected) {
      return rejectWithValue("Socket not connected");
    }

    try {
      socketManager.sendMessage({
        type: "PostMessage",
        thread_id: threadId,
        prompt,
        greeting,
        personality_id: personalityId,
      } as WebSocketPayload);
      return null;
    } catch (error) {
      // Convert ClassifiedError to SerializableError for Redux state
      if (isClassifiedError(error)) {
        return rejectWithValue(toSerializableError(error));
      }
      // Fallback for other error types
      return rejectWithValue({
        message: error instanceof Error ? error.message : "An unknown error occurred",
        type: "unknown" as const,
      });
    }
  }
);

export const cancelThreadMessages = createAsyncThunk(
  "messages/cancelThreadMessages",
  async (threadId: string, thunkAPI) => {
    try {
      await api.post(`/threads/${threadId}/cancel`, {});

      // Mark any in-progress assistant messages for this thread as cancelled
      const state = thunkAPI.getState() as RootState;
      const messages = getMessages(state);

      // Find in-progress assistant messages for this thread
      const inProgressMessages = messages.filter(
        (message) =>
          message.thread_id === threadId &&
          message.type === "ai" &&
          !message.isOptimistic &&
          !message.isCancelled &&
          (!message.status || message.status !== "completed")
      );

      // Mark each in-progress message as cancelled
      inProgressMessages.forEach((message) => {
        thunkAPI.dispatch(markMessageCancelled(message.id));
      });

      return threadId;
    } catch (error) {
      // Convert ClassifiedError to SerializableError for Redux state
      if (isClassifiedError(error)) {
        return thunkAPI.rejectWithValue(toSerializableError(error));
      }
      // Fallback for other error types
      return thunkAPI.rejectWithValue({
        message: error instanceof Error ? error.message : "An unknown error occurred",
        type: "unknown" as const,
      });
    }
  }
);
