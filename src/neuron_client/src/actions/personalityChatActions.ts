import { api } from "@/lib/api";
import { createAsyncThunk } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import {
  addOptimisticMessage,
  markMessageFailed,
  setLoadingMore,
} from "../slices/personalityChatSlice";
import type {
  PersonalityMessagesResponse,
  CreatePersonalityMessageRequest,
  CreatePersonalityMessageResponse,
  UpdatePersonalityMessageRequest,
  UpdatePersonalityMessageResponse,
} from "../types/personalityChat";

export const fetchPersonalityMessages = createAsyncThunk(
  "personalityChat/fetchPersonalityMessages",
  async (
    {
      personalityId,
      roomId,
      limit = 50,
      offset = 0,
    }: {
      personalityId: string;
      roomId: string;
      limit?: number;
      offset?: number;
    },
    thunkAPI
  ) => {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      const response = await api.get<PersonalityMessagesResponse>(
        `/personality-messages/${personalityId}/rooms/${roomId}/messages?${params}`
      );

      return {
        ...response,
        personalityId,
        hasMore: response.personality_messages.length === limit,
      };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const loadMorePersonalityMessages = createAsyncThunk(
  "personalityChat/loadMorePersonalityMessages",
  async (
    {
      personalityId,
      roomId,
      limit = 50,
    }: {
      personalityId: string;
      roomId: string;
      limit?: number;
    },
    thunkAPI
  ) => {
    const state = thunkAPI.getState() as RootState;
    const existingMessages = state.personalityChat.messageIds
      .filter((id) => {
        const message = state.personalityChat.messageMap[id];
        return message.personality_id === personalityId && message.personality_room_id === roomId;
      });

    const offset = existingMessages.length;

    // Set loading state
    thunkAPI.dispatch(setLoadingMore({ personalityId, loading: true }));

    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      const response = await api.get<PersonalityMessagesResponse>(
        `/personality-messages/${personalityId}/rooms/${roomId}/messages?${params}`
      );

      return {
        ...response,
        personalityId,
        hasMore: response.personality_messages.length === limit,
      };
    } catch (error) {
      thunkAPI.dispatch(setLoadingMore({ personalityId, loading: false }));
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const sendPersonalityMessage = createAsyncThunk(
  "personalityChat/sendPersonalityMessage",
  async (
    {
      personalityId,
      roomId,
      content,
      userId,
    }: {
      personalityId: string;
      roomId: string;
      content: string;
      userId: string;
    },
    thunkAPI
  ) => {
    // Generate a temporary ID for the optimistic message
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Add optimistic message immediately
    thunkAPI.dispatch(
      addOptimisticMessage({
        tempId,
        content,
        personalityId,
        roomId,
        userId,
      })
    );

    try {
      const requestBody: CreatePersonalityMessageRequest = {
        content,
        personality_room_id: roomId,
      };

      const response = await api.post<CreatePersonalityMessageResponse>(
        `/personality-messages/${personalityId}`,
        requestBody
      );

      // Add temp_id to the response so we can replace the optimistic message
      return {
        ...response,
        personality_message: {
          ...response.personality_message,
          temp_id: tempId,
        },
      };
    } catch (error) {
      // Mark the optimistic message as failed
      thunkAPI.dispatch(
        markMessageFailed({
          tempId,
          error: error instanceof Error ? error.message : "Failed to send message",
        })
      );

      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const updatePersonalityMessage = createAsyncThunk(
  "personalityChat/updatePersonalityMessage",
  async (
    {
      personalityId,
      messageId,
      content,
    }: {
      personalityId: string;
      messageId: string;
      content: string;
    },
    thunkAPI
  ) => {
    try {
      const requestBody: UpdatePersonalityMessageRequest = {
        content,
      };

      const response = await api.put<UpdatePersonalityMessageResponse>(
        `/personality-messages/${personalityId}/messages/${messageId}`,
        requestBody
      );

      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const deletePersonalityMessage = createAsyncThunk(
  "personalityChat/deletePersonalityMessage",
  async (
    {
      personalityId,
      messageId,
    }: {
      personalityId: string;
      messageId: string;
    },
    thunkAPI
  ) => {
    try {
      await api.delete(
        `/personality-messages/${personalityId}/messages/${messageId}`
      );

      return { messageId, personalityId };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

// Helper action for clearing messages when switching personalities
export const clearPersonalityMessages = createAsyncThunk(
  "personalityChat/clearPersonalityMessages",
  async (personalityId: string) => {
    // This is just a wrapper to dispatch the clearMessages action
    // Useful for consistency and potential future enhancements
    return personalityId;
  }
);
