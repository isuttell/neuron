import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "../store";

export interface RoomSubscription {
  roomType: string;
  roomId: string;
  memberCount: number;
  joinedAt: string;
}

interface RoomState {
  // Map of room keys (type:id) to subscription info
  subscribedRooms: Record<string, RoomSubscription>;
  // Map of room keys to pending join states
  joinPending: Record<string, boolean>;
  // Map of room keys to error messages
  errors: Record<string, string>;
}

const initialState: RoomState = {
  subscribedRooms: {},
  joinPending: {},
  errors: {},
};

// Helper function to create room key
const getRoomKey = (roomType: string, roomId: string): string => `${roomType}:${roomId}`;

const roomSlice = createSlice({
  name: "room",
  initialState,
  reducers: {
    // Start joining a room
    joinRoomStart: (state, action: PayloadAction<{ roomType: string; roomId: string }>) => {
      const { roomType, roomId } = action.payload;
      const roomKey = getRoomKey(roomType, roomId);

      state.joinPending[roomKey] = true;
      delete state.errors[roomKey];
    },

    // Successfully joined a room
    joinRoomSuccess: (state, action: PayloadAction<{ roomType: string; roomId: string; memberCount: number }>) => {
      const { roomType, roomId, memberCount } = action.payload;
      const roomKey = getRoomKey(roomType, roomId);

      state.subscribedRooms[roomKey] = {
        roomType,
        roomId,
        memberCount,
        joinedAt: new Date().toISOString(),
      };

      state.joinPending[roomKey] = false;
      delete state.errors[roomKey];
    },

    // Failed to join a room
    joinRoomFailure: (state, action: PayloadAction<{ roomType: string; roomId: string; error: string }>) => {
      const { roomType, roomId, error } = action.payload;
      const roomKey = getRoomKey(roomType, roomId);

      state.joinPending[roomKey] = false;
      state.errors[roomKey] = error;
      delete state.subscribedRooms[roomKey];
    },

    // Left a room
    leaveRoom: (state, action: PayloadAction<{ roomType: string; roomId: string }>) => {
      const { roomType, roomId } = action.payload;
      const roomKey = getRoomKey(roomType, roomId);

      delete state.subscribedRooms[roomKey];
      delete state.joinPending[roomKey];
      delete state.errors[roomKey];
    },

    // Update member count for a room
    updateMemberCount: (state, action: PayloadAction<{ roomType: string; roomId: string; memberCount: number }>) => {
      const { roomType, roomId, memberCount } = action.payload;
      const roomKey = getRoomKey(roomType, roomId);

      if (state.subscribedRooms[roomKey]) {
        state.subscribedRooms[roomKey].memberCount = memberCount;
      }
    },

    // Clear all room state (e.g., on disconnect)
    clearAllRooms: (state) => {
      state.subscribedRooms = {};
      state.joinPending = {};
      state.errors = {};
    },
  },
});

export const {
  joinRoomStart,
  joinRoomSuccess,
  joinRoomFailure,
  leaveRoom,
  updateMemberCount,
  clearAllRooms,
} = roomSlice.actions;

// Selectors
export const selectRoomSubscription = (state: RootState, roomType: string, roomId: string): RoomSubscription | undefined => {
  const roomKey = getRoomKey(roomType, roomId);
  return state.room.subscribedRooms[roomKey];
};

export const selectIsRoomSubscribed = (state: RootState, roomType: string, roomId: string): boolean => {
  const roomKey = getRoomKey(roomType, roomId);
  return !!state.room.subscribedRooms[roomKey];
};

export const selectRoomJoinPending = (state: RootState, roomType: string, roomId: string): boolean => {
  const roomKey = getRoomKey(roomType, roomId);
  return !!state.room.joinPending[roomKey];
};

export const selectRoomError = (state: RootState, roomType: string, roomId: string): string | undefined => {
  const roomKey = getRoomKey(roomType, roomId);
  return state.room.errors[roomKey];
};

export const selectRoomMemberCount = (state: RootState, roomType: string, roomId: string): number => {
  const subscription = selectRoomSubscription(state, roomType, roomId);
  return subscription?.memberCount || 0;
};

export const selectAllSubscribedRooms = (state: RootState): RoomSubscription[] => {
  return Object.values(state.room.subscribedRooms);
};

export default roomSlice.reducer;
