import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import { fetchMessagesByThread } from "../actions/messageActions";

interface Content {
  text: string;
  type: string;
  index: number;
}

export interface Message {
  id: string;
  type: string;
  content: Content[] | string;
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

interface IncomingMessagesEvent {
  messages: IncomingMessage[];
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
    // created_at: new Date(message.created_at).getTime(),
    // updated_at: new Date(message.updated_at).getTime(),
  };
}

function upsert(state: MessageState, message: Message) {
  const existingMessageIndex = state.messages.findIndex(
    (msg) => msg.id === message.id
  );
  if (existingMessageIndex !== -1) {
    state.messages[existingMessageIndex] = message;
  } else {
    state.messages.push(message);
  }
}

export const messagesSlice = createSlice({
  name: "messages",
  initialState,
  reducers: {
    upsertMessage: (state, action: PayloadAction<IncomingMessageEvent>) => {
      upsert(state, action.payload.message);
    },
    upsertMessages: (state, action: PayloadAction<IncomingMessagesEvent>) => {
      for (const message of action.payload.messages) {
        upsert(state, message);
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
        if (typeof message.content === "string") {
          state.messages[existingMessageIndex].content += message.content;
        }
      } else {
        state.messages.push(message);
      }
    },
  },
  extraReducers: (builder) => {
    builder.addCase(
      fetchMessagesByThread.fulfilled,
      (state, action: PayloadAction<IncomingMessagesEvent>) => {
        for (const message of action.payload.messages) {
          upsert(state, message);
        }
      }
    );
  },
});

export const { upsertMessage, upsertMessages, partialMessage } =
  messagesSlice.actions;

export const getMessages = (state: RootState) => state.messages.messages;

export default messagesSlice.reducer;
