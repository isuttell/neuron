import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice, createSelector } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as personalityRoomActions from "../actions/personalityRoomActions";
import * as threadActions from "../actions/threadActions";
import type {
  PersonalityRoom,
  PersonalityRoomUser,
  PersonalityRoomsResponse,
  PersonalityRoomResponse,
} from "../types/personalityRoom";
import type { User } from "../types/user";
import type { SerializableError } from "../types/error";

// WebSocket event types
export interface PersonalityRoomCreatedEvent {
  type: "personality_room_created";
  personality_id: string;
  room_id: string;
  name: string;
  room_type: string;
  created_by: string | null;
  message_count: number;
}

export interface PersonalityRoomUpdatedEvent {
  type: "personality_room_updated";
  personality_id: string;
  room_id: string;
  name: string;
  room_type: string;
}

export interface PersonalityRoomDeletedEvent {
  type: "personality_room_deleted";
  personality_id: string;
  room_id: string;
}

export interface UserJoinedPersonalityRoomEvent {
  type: "user_joined_personality_room";
  personality_id: string;
  room_id: string;
  user_id: string;
  role: string;
}

export interface UserLeftPersonalityRoomEvent {
  type: "user_left_personality_room";
  personality_id: string;
  room_id: string;
  user_id: string;
}

export interface PersonalityRoomDataEvent {
  type: "personality_room_data";
  personality_room: PersonalityRoom;
  personality_room_users: PersonalityRoomUser[];
  users: User[]; // Users are handled by usersSlice
}

interface PersonalityRoomState {
  roomMap: Record<string, PersonalityRoom>;
  roomIds: string[];
  roomUsers: Record<string, PersonalityRoomUser[]>; // roomId -> users
  loading: boolean;
  error: SerializableError | null;
}

const initialState: PersonalityRoomState = {
  roomMap: {},
  roomIds: [],
  roomUsers: {},
  loading: false,
  error: null,
};

function upsertRoom(state: PersonalityRoomState, room: PersonalityRoom) {
  const roomId = room.id;

  if (!state.roomMap[roomId]) {
    state.roomIds.push(roomId);
  }
  state.roomMap[roomId] = room;
}

function upsertRoomUsers(state: PersonalityRoomState, roomId: string, users: PersonalityRoomUser[]) {
  state.roomUsers[roomId] = users;
}

export const personalityRoomSlice = createSlice({
  name: "personalityRoom",
  initialState,
  reducers: {
    // WebSocket event handlers
    handleRoomCreated: (state, action: PayloadAction<PersonalityRoomCreatedEvent>) => {
      const { room_id, personality_id, name, room_type, created_by, message_count } = action.payload;
      const room: PersonalityRoom = {
        id: room_id,
        personality_id,
        name,
        type: room_type,
        created_by,
        message_count,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      upsertRoom(state, room);
    },

    handleRoomUpdated: (state, action: PayloadAction<PersonalityRoomUpdatedEvent>) => {
      const { room_id, name, room_type } = action.payload;
      if (state.roomMap[room_id]) {
        state.roomMap[room_id].name = name;
        state.roomMap[room_id].type = room_type;
        state.roomMap[room_id].updated_at = new Date().toISOString();
      }
    },

    handleRoomDeleted: (state, action: PayloadAction<PersonalityRoomDeletedEvent>) => {
      const { room_id } = action.payload;
      delete state.roomMap[room_id];
      delete state.roomUsers[room_id];
      state.roomIds = state.roomIds.filter(id => id !== room_id);
    },

    handleUserJoined: (state, action: PayloadAction<UserJoinedPersonalityRoomEvent>) => {
      const { room_id, user_id, role } = action.payload;
      if (!state.roomUsers[room_id]) {
        state.roomUsers[room_id] = [];
      }

      // Check if user already exists
      const existingIndex = state.roomUsers[room_id].findIndex(u => u.user_id === user_id);
      if (existingIndex === -1) {
        state.roomUsers[room_id].push({
          user_id,
          personality_room_id: room_id,
          role,
        });
      }
    },

    handleUserLeft: (state, action: PayloadAction<UserLeftPersonalityRoomEvent>) => {
      const { room_id, user_id } = action.payload;
      if (state.roomUsers[room_id]) {
        state.roomUsers[room_id] = state.roomUsers[room_id].filter(u => u.user_id !== user_id);
      }
    },

    handleRoomStatusUpdate: (state, action: PayloadAction<{ room_id: string; status: string }>) => {
      const { room_id, status } = action.payload;
      if (state.roomMap[room_id]) {
        state.roomMap[room_id].status = status || null;
      }
    },

    handleRoomData: (state, action: PayloadAction<PersonalityRoomDataEvent>) => {
      const { personality_room, personality_room_users } = action.payload;

      // Upsert the room
      upsertRoom(state, personality_room);

      // Update room users
      if (personality_room_users && personality_room_users.length > 0) {
        upsertRoomUsers(state, personality_room.id, personality_room_users);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch personality rooms
      .addCase(personalityRoomActions.fetchPersonalityRooms.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(personalityRoomActions.fetchPersonalityRooms.fulfilled, (state, action: PayloadAction<PersonalityRoomsResponse>) => {
        state.loading = false;
        const { personality_rooms, personality_room_users } = action.payload;

        // Clear existing rooms for this personality
        const personalityId = personality_rooms[0]?.personality_id;
        if (personalityId) {
          const roomsToRemove = state.roomIds.filter(
            id => state.roomMap[id]?.personality_id === personalityId
          );
          roomsToRemove.forEach(id => {
            delete state.roomMap[id];
            delete state.roomUsers[id];
          });
          state.roomIds = state.roomIds.filter(id => !roomsToRemove.includes(id));
        }

        // Add new rooms
        personality_rooms.forEach(room => upsertRoom(state, room));

        // Process room users
        if (personality_room_users) {
          const usersByRoom: Record<string, PersonalityRoomUser[]> = {};
          personality_room_users.forEach(user => {
            if (!usersByRoom[user.personality_room_id]) {
              usersByRoom[user.personality_room_id] = [];
            }
            usersByRoom[user.personality_room_id].push(user);
          });

          Object.entries(usersByRoom).forEach(([roomId, users]) => {
            upsertRoomUsers(state, roomId, users);
          });
        }
      })
      .addCase(personalityRoomActions.fetchPersonalityRooms.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as SerializableError || null;
      })

      // Create personality room
      .addCase(personalityRoomActions.createPersonalityRoom.fulfilled, (state, action: PayloadAction<PersonalityRoomResponse>) => {
        const { personality_room } = action.payload;
        upsertRoom(state, personality_room);
      })

      // Get personality room
      .addCase(personalityRoomActions.getPersonalityRoom.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(personalityRoomActions.getPersonalityRoom.fulfilled, (state, action: PayloadAction<PersonalityRoomResponse>) => {
        state.loading = false;
        const { personality_room, personality_room_users } = action.payload;
        upsertRoom(state, personality_room);

        if (personality_room_users) {
          upsertRoomUsers(state, personality_room.id, personality_room_users);
        }
      })
      .addCase(personalityRoomActions.getPersonalityRoom.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as SerializableError; // Store the serializable error object
      })

      // Update personality room
      .addCase(personalityRoomActions.updatePersonalityRoom.fulfilled, (state, action: PayloadAction<PersonalityRoomResponse>) => {
        const { personality_room } = action.payload;
        upsertRoom(state, personality_room);
      })

      // Delete personality room
      .addCase(personalityRoomActions.deletePersonalityRoom.fulfilled, (state, action: PayloadAction<string>) => {
        const roomId = action.payload;
        delete state.roomMap[roomId];
        delete state.roomUsers[roomId];
        state.roomIds = state.roomIds.filter(id => id !== roomId);
      })

      // Add room user
      .addCase(personalityRoomActions.addPersonalityRoomUser.fulfilled, (state, action) => {
        const { roomId, personality_room_user } = action.payload;
        if (!state.roomUsers[roomId]) {
          state.roomUsers[roomId] = [];
        }

        const existingIndex = state.roomUsers[roomId].findIndex(
          u => u.user_id === personality_room_user.user_id
        );
        if (existingIndex === -1) {
          state.roomUsers[roomId].push(personality_room_user);
        }
      })

      // Update room user
      .addCase(personalityRoomActions.updatePersonalityRoomUser.fulfilled, (state, action) => {
        const { roomId, personality_room_user } = action.payload;
        if (state.roomUsers[roomId]) {
          const userIndex = state.roomUsers[roomId].findIndex(
            u => u.user_id === personality_room_user.user_id
          );
          if (userIndex !== -1) {
            state.roomUsers[roomId][userIndex] = {
              user_id: personality_room_user.user_id,
              personality_room_id: personality_room_user.personality_room_id,
              role: personality_room_user.role,
            };
          }
        }
      })

      // Remove room user
      .addCase(personalityRoomActions.removePersonalityRoomUser.fulfilled, (state, action) => {
        const { roomId, userId } = action.payload;
        if (state.roomUsers[roomId]) {
          state.roomUsers[roomId] = state.roomUsers[roomId].filter(u => u.user_id !== userId);
        }
      })

      // Handle combined fetch results
      .addCase(threadActions.fetchRecentCombinedItems.fulfilled, (state, action) => {
        // Handle personality rooms from the combined response
        if (action.payload?.personality_rooms) {
          for (const room of action.payload.personality_rooms) {
            upsertRoom(state, room);
          }

          // Update room IDs
          state.roomIds = Array.from(new Set([
            ...state.roomIds,
            ...action.payload.personality_rooms.map(room => room.id)
          ]));
        }

        // Handle personality room users from the combined response
        if (action.payload?.personality_room_users) {
          // Group room users by room ID
          const roomUsersByRoomId: Record<string, PersonalityRoomUser[]> = {};
          for (const roomUser of action.payload.personality_room_users) {
            const roomId = roomUser.personality_room_id;
            if (!roomUsersByRoomId[roomId]) {
              roomUsersByRoomId[roomId] = [];
            }
            roomUsersByRoomId[roomId].push({
              user_id: roomUser.user_id,
              personality_room_id: roomUser.personality_room_id,
              role: roomUser.role,
            });
          }

          // Update room users
          for (const [roomId, users] of Object.entries(roomUsersByRoomId)) {
            upsertRoomUsers(state, roomId, users);
          }
        }
      });
  },
});

export const {
  handleRoomCreated,
  handleRoomUpdated,
  handleRoomDeleted,
  handleUserJoined,
  handleUserLeft,
  handleRoomStatusUpdate,
  handleRoomData,
} = personalityRoomSlice.actions;

// Base selectors
const selectPersonalityRoomState = (state: RootState) => state.personalityRoom;
const selectRoomIds = (state: RootState) => state.personalityRoom.roomIds;
const selectRoomMap = (state: RootState) => state.personalityRoom.roomMap;
const selectRoomUsers = (state: RootState) => state.personalityRoom.roomUsers;

// Memoized selectors
export const getPersonalityRoomLoading = createSelector(
  [selectPersonalityRoomState],
  (state) => state.loading
);

export const getPersonalityRoomError = createSelector(
  [selectPersonalityRoomState],
  (state) => state.error
);

export const getAllPersonalityRooms = createSelector(
  [selectRoomIds, selectRoomMap],
  (roomIds, roomMap) => roomIds.map(id => roomMap[id])
);

export const getPersonalityRoom = createSelector(
  [selectRoomMap, (_, id: string) => id],
  (roomMap, id) => roomMap[id]
);

export const getPersonalityRooms = createSelector(
  [getAllPersonalityRooms, (_, personalityId?: string) => personalityId],
  (rooms, personalityId) =>
    rooms.filter(room =>
      personalityId ? room.personality_id === personalityId : true
    )
);

export const getRoomUsers = createSelector(
  [selectRoomUsers, (_, roomId: string) => roomId],
  (roomUsers, roomId) => roomUsers[roomId] || []
);

export default personalityRoomSlice.reducer;
