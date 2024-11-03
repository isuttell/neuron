import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import WebSocketManager from "../WebSocketManager";
import type { PayloadAction } from "@reduxjs/toolkit";

// Define a type for the slice state
interface SocketState {
  connected: boolean;
  socket: WebSocketManager | null;
}

// Define the initial state using that type
const initialState: SocketState = {
  connected: false,
  socket: null,
};

export const socketSlice = createSlice({
  name: "socket",
  initialState,
  reducers: {
    connect: (state, action: PayloadAction<WebSocketManager>) => {
      state.connected = true;
      state.socket = action.payload;
    },
    disconnect: (state) => {
      state.connected = false;
    },
  },
});

export const { connect, disconnect } = socketSlice.actions;

export const getConnectionStatus = (state: RootState) => state.socket.connected;

export const getSocket = (state: RootState) => state.socket.socket;

export default socketSlice.reducer;
