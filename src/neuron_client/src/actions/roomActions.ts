import { createAsyncThunk } from "@reduxjs/toolkit";
import { socketManager } from "../WebSocketManager";
import { getConnectionStatus } from "../slices/socketSlice";
import { RootState } from "../store";
import { WebSocketPayload } from "../types/websocket";

export const joinPersonalityRoom = createAsyncThunk(
  "room/joinPersonalityRoom",
  async (
    {
      personalityId,
      roomId,
    }: {
      personalityId: string;
      roomId: string;
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
        type: "JoinPersonalityRoom",
        personality_id: personalityId,
        room_id: roomId,
      } as WebSocketPayload);

      return { personalityId, roomId };
    } catch (error) {
      if (error instanceof Error) {
        return rejectWithValue(error.message);
      }
      return rejectWithValue("Failed to join personality room");
    }
  }
);

export const leavePersonalityRoom = createAsyncThunk(
  "room/leavePersonalityRoom",
  async (
    {
      personalityId,
      roomId,
    }: {
      personalityId: string;
      roomId: string;
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
        type: "LeavePersonalityRoom",
        personality_id: personalityId,
        room_id: roomId,
      } as WebSocketPayload);

      return { personalityId, roomId };
    } catch (error) {
      if (error instanceof Error) {
        return rejectWithValue(error.message);
      }
      return rejectWithValue("Failed to leave personality room");
    }
  }
);
