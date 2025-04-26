import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import { fetchMessagesByThread } from "../actions/messageActions";
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
  },
  extraReducers: (builder) => {
    builder.addCase(
      fetchMessagesByThread.fulfilled,
      (state, action: PayloadAction<MessageResponse>) => {
        if (action.payload.users) {
          for (const user of action.payload.users) {
            upsertUser(state, user);
          }
        }
      }
    );
  },
});

export const { reset } = usersSlice.actions;
export const getUsers = (state: RootState) => state.users.users;
export const getUser = (state: RootState, id: string) => state.users.users[id];

export default usersSlice.reducer;
