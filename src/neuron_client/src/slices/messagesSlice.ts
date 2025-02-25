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

export function getThinkingContent(content: Content[] | string): string {
  if (typeof content === "string") {
    return ""; // String content doesn't contain thinking
  }
  return content
    .filter(
      (item): item is ThinkingContent =>
        item.type === "thinking" &&
        typeof (item as ThinkingContent).thinking === "string"
    )
    .map((item) => item.thinking)
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

        // Handle content based on type
        let updatedContent: Content[] | string;

        if (
          typeof message.content === "string" &&
          typeof existingMessage.content === "string"
        ) {
          // If both are strings, concatenate as before
          updatedContent = existingMessage.content + message.content;
        } else if (
          Array.isArray(existingMessage.content) &&
          Array.isArray(message.content)
        ) {
          // Create a map of existing content by type
          const contentByType: Record<string, Content> = {};

          // Initialize with existing content
          (existingMessage.content as Content[]).forEach((item: Content) => {
            contentByType[item.type] = { ...item };
          });

          // Merge with new content
          (message.content as Content[]).forEach((newItem: Content) => {
            if (contentByType[newItem.type]) {
              // If this type already exists, concatenate the content
              const existingItem = contentByType[newItem.type];

              if (
                newItem.type === "text" &&
                "text" in newItem &&
                "text" in existingItem
              ) {
                contentByType[newItem.type] = {
                  ...existingItem,
                  text: existingItem.text + newItem.text,
                };
              } else if (
                newItem.type === "thinking" &&
                "thinking" in newItem &&
                "thinking" in existingItem
              ) {
                contentByType[newItem.type] = {
                  ...existingItem,
                  thinking: existingItem.thinking + newItem.thinking,
                };
              }
            } else {
              // If this type doesn't exist yet, add it
              contentByType[newItem.type] = { ...newItem };
            }
          });

          // Convert back to array
          updatedContent = Object.values(contentByType);
        } else {
          // If types don't match or other cases, use the new content
          updatedContent = message.content;
        }

        state.messageMap[messageId] = {
          ...existingMessage,
          status: message.status,
          content: updatedContent,
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
