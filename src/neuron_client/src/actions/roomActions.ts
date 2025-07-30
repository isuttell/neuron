import { createAsyncThunk } from "@reduxjs/toolkit";
import { socketManager } from "../WebSocketManager";
import { getConnectionStatus } from "../slices/socketSlice";
import { selectIsRoomSubscribed } from "../slices/roomSlice";
import { RootState } from "../store";
import { WebSocketPayload, RoomJoinedEvent } from "../types/websocket";

const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAYS = [1000, 2000, 4000]; // Exponential backoff: 1s, 2s, 4s

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

    // Function to wait for room_joined event
    const waitForJoinConfirmation = (): Promise<void> => {
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          listener.remove();
          reject(new Error("Timeout waiting for room join confirmation"));
        }, 5000); // 5 second timeout for each attempt

        const listener = socketManager.on("room_joined", (event: RoomJoinedEvent) => {
          if (event.room_type === "personality_room" && event.room_id === roomId) {
            clearTimeout(timeout);
            listener.remove();
            resolve();
          }
        });
      });
    };

    // Retry logic with exponential backoff
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < MAX_RETRY_ATTEMPTS; attempt++) {
      try {
        // Check if already subscribed (might have succeeded in a previous attempt)
        const currentState = getState() as RootState;
        if (selectIsRoomSubscribed(currentState, "personality_room", roomId)) {
          return { personalityId, roomId };
        }

        // Send join message
        socketManager.sendMessage({
          type: "JoinPersonalityRoom",
          personality_id: personalityId,
          room_id: roomId,
        } as WebSocketPayload);

        // Wait for confirmation
        await waitForJoinConfirmation();

        return { personalityId, roomId };
      } catch (error) {
        lastError = error instanceof Error ? error : new Error("Failed to join personality room");

        // If this isn't the last attempt, wait before retrying
        if (attempt < MAX_RETRY_ATTEMPTS - 1) {
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAYS[attempt]));
        }
      }
    }

    // All retries failed
    return rejectWithValue(lastError?.message || "Failed to join personality room after multiple attempts");
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
