import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import { fetchMessagesByThread } from "../actions/messageActions";
interface Content {
  text: string;
  type: string;
  index: number;
}

type MessageRole = "ai" | "human" | "tool" | "system";

interface UsageMetadata extends Record<string, any> {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
}

export interface Message {
  id: string;
  name?: string;
  type: MessageRole;
  content: Content[] | string;
  thread_id: string;
  status?: string;
  tool_calls?: any[];
  tool_call_id?: string;
  additional_kwargs?: any;
  response_metadata?: any;
  usage_metadata?: UsageMetadata;
  created_at?: number;
  node?: string;
}

interface IncomingMessage extends Omit<Message, "created_at"> {
  created_at: string;
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

// Update MessageState to use a Record/map instead of array
interface MessageState {
  messageMap: Record<string, Message>;
  messageIds: string[]; // To maintain order
  loading: boolean;
  error: string | null;
}

// Update initial state
const initialState: MessageState = {
  messageMap: {},
  messageIds: [],
  loading: false,
  error: null,
};

export function getTextContent(content: Content[] | string): string {
  if (typeof content === "string") {
    return content;
  }
  return content
    .filter((item) => item.type === "text" && typeof item.text === "string")
    .map((item) => item.text)
    .join("\n");
}

/**
 * Parses an incoming message dates and returns a Message object
 * @param message - The incoming message
 * @returns A Message object
 */
function parseIncomingMessage(message: IncomingMessage): Message {
  return {
    ...message,
    id: message.id.replace("run-", ""),
    created_at: message.created_at
      ? new Date(message.created_at).getTime()
      : undefined,
  };
}

function upsert(state: MessageState, incomingMessage: IncomingMessage) {
  const message = parseIncomingMessage(incomingMessage);
  const messageId = message.id;

  if (!state.messageMap[messageId]) {
    state.messageIds.push(messageId);
  }
  state.messageMap[messageId] = message;
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
      const messageId = action.payload.message.id.replace("run-", "");
      const existingMessage = state.messageMap[messageId];

      if (existingMessage) {
        const message = action.payload.message;
        state.messageMap[messageId] = {
          ...existingMessage,
          status: message.status,
          content:
            typeof message.content === "string"
              ? existingMessage.content + message.content
              : message.content,
        };
      } else {
        const message = parseIncomingMessage(action.payload.message);
        state.messageMap[messageId] = message;
        state.messageIds.push(messageId);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMessagesByThread.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMessagesByThread.rejected, (state) => {
        state.loading = false;
        state.error = "Failed to fetch messages";
      })
      .addCase(
        fetchMessagesByThread.fulfilled,
        (state, action: PayloadAction<IncomingMessagesEvent>) => {
          for (const message of action.payload.messages) {
            upsert(state, message);
          }
          state.loading = false;
        }
      );
  },
});

export const { upsertMessage, upsertMessages, partialMessage } =
  messagesSlice.actions;

export const getMessagesLoading = (state: RootState) => state.messages.loading;
export const getMessagesError = (state: RootState) => state.messages.error;

// Update selector to return messages in order
export const getMessages = (state: RootState) =>
  state.messages.messageIds.map((id) => state.messages.messageMap[id]);

export const getMessage = (state: RootState, id: string) =>
  state.messages.messageMap[id];

export const selectThreadMessages = (state: RootState, threadId?: string) =>
  state.messages.messageIds
    .map((id) => state.messages.messageMap[id])
    .filter((message) => message.thread_id === threadId);

export default messagesSlice.reducer;
