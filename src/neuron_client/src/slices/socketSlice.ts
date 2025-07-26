import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "../store";

// Define a type for the slice state
interface SocketState {
  connected: boolean;
}

// Define the initial state using that type
const initialState: SocketState = {
  connected: false,
};

export const socketSlice = createSlice({
  name: "socket",
  initialState,
  reducers: {
    connect: (state) => {
      state.connected = true;
    },
    disconnect: (state) => {
      state.connected = false;
    },
  },
});

export const { connect, disconnect } = socketSlice.actions;

export const getConnectionStatus = (state: RootState) => state.socket.connected;

export default socketSlice.reducer;
