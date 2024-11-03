import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

interface Message {
  id: string;
  role: string;
  content: string;
  created_at: string;
  thread_id: string;
  status?: string;
}

interface IncomingPartialMessage extends Message {
  index: number;
  status: string;
}

interface IncomingMessageEvent {
  message: Message;
}

interface IncomingPartialMessageEvent {
  message: IncomingPartialMessage;
}

// Define a type for the slice state
interface MessageState {
  messages: Message[];
}

// Define the initial state using that type
const initialState: MessageState = {
  messages: [],
};

export const messagesSlice = createSlice({
  name: "messages",
  initialState,
  reducers: {
    upsertMessage: (state, action: PayloadAction<IncomingMessageEvent>) => {
      const existingMessageIndex = state.messages.findIndex(
        (msg) => msg.id === action.payload.message.id
      );
      const message: Message = action.payload.message;
      if (existingMessageIndex !== -1) {
        state.messages[existingMessageIndex] = message;
      } else {
        state.messages.push(message);
      }
    },
    partialMessage: (
      state,
      action: PayloadAction<IncomingPartialMessageEvent>
    ) => {
      const existingMessageIndex = state.messages.findIndex(
        (msg) => msg.id === action.payload.message.id
      );
      const message: Message = action.payload.message;
      if (existingMessageIndex !== -1) {
        state.messages[existingMessageIndex].status = message.status;
        state.messages[existingMessageIndex].content += message.content;
      } else {
        state.messages.push(message);
      }
    },
  },
});

export const { upsertMessage, partialMessage } = messagesSlice.actions;

export const getMessages = (state: RootState) => state.messages.messages;

export default messagesSlice.reducer;
