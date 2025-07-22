import { createAsyncThunk } from "@reduxjs/toolkit";
import { getSocket } from "../slices/socketSlice";
import { RootState } from "../store";
import { WebSocketPayload } from "../types/websocket";

export const joinPersonalityRoom = createAsyncThunk(
  "room/joinPersonalityRoom",
  async (
    {
      personalityId,
    }: {
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
        type: "JoinPersonalityRoom",
        personality_id: personalityId,
      } as WebSocketPayload);

      return { personalityId };
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
    }: {
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
        type: "LeavePersonalityRoom",
        personality_id: personalityId,
      } as WebSocketPayload);

      return { personalityId };
    } catch (error) {
      if (error instanceof Error) {
        return rejectWithValue(error.message);
      }
      return rejectWithValue("Failed to leave personality room");
    }
  }
);
