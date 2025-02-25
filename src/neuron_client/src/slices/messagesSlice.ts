import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import { fetchMessagesByThread } from "../actions/messageActions";
import type { RootState } from "../store";
import { MessageResponse } from "../types/message";

// Base content interface with common properties
interface BaseContent {
  type: string;
  index: number;
}

// Text content
interface TextContent extends BaseContent {
  type: "text";
  text: string;
}

// Thinking content
interface ThinkingContent extends BaseContent {
  type: "thinking";
  thinking: string;
}

// Union type for all content types
type Content = TextContent | ThinkingContent | BaseContent;

type MessageRole = "ai" | "human" | "tool" | "system";

interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

interface AdditionalKwargs {
  [key: string]: string | number | boolean | null;
}

interface ResponseMetadata {
  model?: string;
  finish_reason?: string;
  [key: string]: string | number | boolean | null | undefined;
}

interface UsageMetadata {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  [key: string]: number | undefined;
}

export interface IncomingMessage {
  id: string;
  name?: string;
  type: MessageRole;
  content: Content[] | string;
  thread_id: string;
  status?: string;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
  additional_kwargs?: AdditionalKwargs;
  response_metadata?: ResponseMetadata;
  usage_metadata?: UsageMetadata;
  created_at: string;
  node?: string;
}

export interface Message extends Omit<IncomingMessage, "created_at"> {
  created_at?: number;
  updated_at?: number;
  textContent: string;
  thinkingContent?: string;
}

interface IncomingPartialMessage extends Omit<IncomingMessage, "status"> {
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
    .filter(
      (item): item is TextContent =>
        item.type === "text" && typeof (item as TextContent).text === "string"
    )
    .map((item) => item.text)
    .join("\n");
}

export function getThinkingContent(
  content: Content[] | string
): string | undefined {
  if (typeof content === "string") {
    return ""; // String content doesn't contain thinking
  }
  const thinking = content.find(
    (item): item is ThinkingContent =>
      item.type === "thinking" &&
      typeof (item as ThinkingContent).thinking === "string"
  );
  return thinking?.thinking;
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
    textContent: getTextContent(message.content),
    thinkingContent: getThinkingContent(message.content),
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
      const incomingMessage = action.payload.message;

      if (existingMessage) {
        // Extract text and thinking from the incoming message
        const incomingTextContent = getTextContent(incomingMessage.content);
        const incomingThinkingContent = getThinkingContent(
          incomingMessage.content
        );
        // Update the message with concatenated text and thinking content
        state.messageMap[messageId] = {
          ...existingMessage,
          status: incomingMessage.status,
          updated_at: Date.now(),
          // Concatenate the text and thinking content with proper newline handling
          textContent: existingMessage.textContent
            ? existingMessage.textContent +
              (incomingTextContent ? "\n" + incomingTextContent : "")
            : incomingTextContent,
          thinkingContent: existingMessage.thinkingContent
            ? existingMessage.thinkingContent + (incomingThinkingContent || "")
            : incomingThinkingContent,
        };
      } else {
        // For new messages, use parseIncomingMessage to set all fields correctly
        const message = parseIncomingMessage(incomingMessage);
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
      .addCase(fetchMessagesByThread.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch messages";
      })
      .addCase(
        fetchMessagesByThread.fulfilled,
        (state, action: PayloadAction<MessageResponse>) => {
          state.loading = false;
          for (const message of action.payload.messages) {
            if (message.created_at) {
              upsert(state, {
                ...message,
                created_at: message.created_at,
              } as IncomingMessage);
            }
          }
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
