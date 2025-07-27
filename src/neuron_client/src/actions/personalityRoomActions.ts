import { createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "@/lib/api";
import type {
  PersonalityRoomUser,
  PersonalityRoomsResponse,
  PersonalityRoomResponse,
  CreatePersonalityRoomRequest,
  UpdatePersonalityRoomRequest,
  PersonalityRoomUserRequest,
} from "../types/personalityRoom";
import type { User } from "../types/user";

export const fetchPersonalityRooms = createAsyncThunk(
  "personalityRoom/fetchRooms",
  async (personalityId: string, thunkAPI) => {
    try {
      const response = await api.get<PersonalityRoomsResponse>(
        `/personality-rooms/${personalityId}`
      );
      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to fetch personality rooms");
    }
  }
);

export const createPersonalityRoom = createAsyncThunk(
  "personalityRoom/create",
  async ({ personalityId, data }: { personalityId: string; data: CreatePersonalityRoomRequest }, thunkAPI) => {
    try {
      const response = await api.post<PersonalityRoomResponse>(
        `/personality-rooms/${personalityId}`,
        data
      );
      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to create personality room");
    }
  }
);

export const getPersonalityRoom = createAsyncThunk(
  "personalityRoom/getRoom",
  async ({ personalityId, roomId }: { personalityId: string; roomId: string }, thunkAPI) => {
    try {
      const response = await api.get<PersonalityRoomResponse>(
        `/personality-rooms/${personalityId}/rooms/${roomId}`
      );
      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to fetch personality room");
    }
  }
);

export const updatePersonalityRoom = createAsyncThunk(
  "personalityRoom/update",
  async ({ personalityId, roomId, data }: { personalityId: string; roomId: string; data: UpdatePersonalityRoomRequest }, thunkAPI) => {
    try {
      const response = await api.put<PersonalityRoomResponse>(
        `/personality-rooms/${personalityId}/rooms/${roomId}`,
        data
      );
      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to update personality room");
    }
  }
);

export const deletePersonalityRoom = createAsyncThunk(
  "personalityRoom/delete",
  async ({ personalityId, roomId }: { personalityId: string; roomId: string }, thunkAPI) => {
    try {
      await api.delete(`/personality-rooms/${personalityId}/rooms/${roomId}`);
      return roomId;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to delete personality room");
    }
  }
);

export const addPersonalityRoomUser = createAsyncThunk(
  "personalityRoom/addUser",
  async ({ personalityId, roomId, data }: { personalityId: string; roomId: string; data: PersonalityRoomUserRequest }, thunkAPI) => {
    try {
      const response = await api.post<{ user: User; personality_room_user: PersonalityRoomUser }>(
        `/personality-rooms/${personalityId}/rooms/${roomId}/users`,
        data
      );
      return { ...response, roomId };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to add user to room");
    }
  }
);

export const removePersonalityRoomUser = createAsyncThunk(
  "personalityRoom/removeUser",
  async ({ personalityId, roomId, userId }: { personalityId: string; roomId: string; userId: string }, thunkAPI) => {
    try {
      await api.delete(`/personality-rooms/${personalityId}/rooms/${roomId}/users/${userId}`);
      return { roomId, userId };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("Failed to remove user from room");
    }
  }
);
