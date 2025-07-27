import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice, createSelector } from "@reduxjs/toolkit";
import { fetchMessagesByThread } from "../actions/messageActions";
import { addUserByEmail } from "../actions/threadActions";
import { fetchPersonalityMessages, loadMorePersonalityMessages } from "../actions/personalityChatActions";
import { fetchPersonality, fetchPersonalities, fetchPersonalityUsers, addPersonalityUser, updatePersonalityUserRole, removePersonalityUser } from "../actions/personalityActions";
import type { RootState } from "../store";
import { MessageResponse } from "../types/message";
import { User } from "../types/user";

interface UserState {
  users: Record<string, User>;
  loading: boolean;
  error: string | null;
}

const initialState: UserState = {
  users: {},
  loading: false,
  error: null,
};

function upsertUser(state: UserState, user: User) {
  state.users[user.id] = user;
}

export const usersSlice = createSlice({
  name: "users",
  initialState,
  reducers: {
    reset: (state) => {
      state.users = {};
      state.loading = false;
      state.error = null;
    },
    upsertUsers: (state, action: PayloadAction<User[]>) => {
      for (const user of action.payload) {
        upsertUser(state, user);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(
        fetchMessagesByThread.fulfilled,
        (state, action: PayloadAction<MessageResponse>) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        addUserByEmail.fulfilled,
        (state, action) => {
          // Check if the action payload has a user property
          if (action.payload?.user) {
            upsertUser(state, action.payload.user);
          }
        }
      )
      .addCase(
        fetchPersonalityMessages.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        loadMorePersonalityMessages.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        fetchPersonality.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        fetchPersonalities.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        fetchPersonalityUsers.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        addPersonalityUser.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        updatePersonalityUserRole.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      )
      .addCase(
        removePersonalityUser.fulfilled,
        (state, action) => {
          if (action.payload.users) {
            for (const user of action.payload.users) {
              upsertUser(state, user);
            }
          }
        }
      );
  },
});

export const { reset, upsertUsers } = usersSlice.actions;

// Base selectors
const selectUsersState = (state: RootState) => state.users;

// Memoized selectors
export const getUsers = createSelector(
  [selectUsersState],
  (usersState) => usersState?.users || {}
);

export const getUser = createSelector(
  [getUsers, (_, id: string) => id],
  (users, id) => users[id]
);

export default usersSlice.reducer;
