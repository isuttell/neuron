import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

export interface Message {
  id: string;
  role: string;
  content: string;
  created_at: number;
  updated_at: number;
  thread_id: string;
  status?: string;
}

interface IncomingMessage extends Omit<Message, "created_at" | "updated_at"> {
  created_at: string;
  updated_at: string;
}

interface IncomingPartialMessage extends IncomingMessage {
  index: number;
  status: string;
}

interface IncomingMessageEvent {
  message: IncomingMessage;
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

/**
 * Parses an incoming message dates and returns a Message object
 * @param message - The incoming message
 * @returns A Message object
 */
function parseIncomingMessage(message: IncomingMessage): Message {
  return {
    ...message,
    created_at: new Date(message.created_at).getTime(),
    updated_at: new Date(message.updated_at).getTime(),
  };
}

export const messagesSlice = createSlice({
  name: "messages",
  initialState,
  reducers: {
    upsertMessage: (state, action: PayloadAction<IncomingMessageEvent>) => {
      const existingMessageIndex = state.messages.findIndex(
        (msg) => msg.id === action.payload.message.id
      );
      const message = parseIncomingMessage(action.payload.message);
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
      const message = parseIncomingMessage(action.payload.message);
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
