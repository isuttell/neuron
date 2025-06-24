import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice, createSelector } from "@reduxjs/toolkit";
import { fetchMessagesByThread } from "../actions/messageActions";
import type { RootState } from "../store";
import { MessageResponse } from "../types/message";

// Base content interface with common properties
interface BaseContent {
  type: string;
  index: number;
}

// Citation interface
export interface Citation {
  type: "char_location";
  cited_text: string;
  document_index: number;
  document_title: string;
  start_char_index: number;
  end_char_index: number;
}

// Text content
interface TextContent extends BaseContent {
  type: "text";
  text: string;
  citations?: Citation[];
}

// Thinking content
interface ThinkingContent extends BaseContent {
  type: "thinking";
  thinking: string;
}

// Image content from tool artifacts
export interface ImageContent extends BaseContent {
  type: "image";
  id: string;
  url: string;
  caption: string;
  description?: string;
  metadata: Record<string, unknown>;
}

// Audio content from tool artifacts
export interface AudioContent extends BaseContent {
  type: "audio";
  id: string;
  url: string;
  caption: string;
  description?: string;
  duration?: number;
  metadata: Record<string, unknown>;
}

// Video content from tool artifacts
export interface VideoContent extends BaseContent {
  type: "video";
  id: string;
  url: string;
  caption: string;
  description?: string;
  duration?: number;
  metadata: Record<string, unknown>;
}

// Union type for all content types
export type Content =
  | TextContent
  | ThinkingContent
  | ImageContent
  | AudioContent
  | VideoContent
  | BaseContent;

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
  user_id?: string;
  artifact?: {
    type: string;
    media_type?: string;
    items?: Array<{
      id: string;
      url: string;
      caption: string;
      description?: string;
      duration?: number;
      metadata?: Record<string, unknown>;
    }>;
  };
}

export interface Message extends Omit<IncomingMessage, "created_at"> {
  created_at?: number;
  updated_at?: number;
  textContent: string;
  thinkingContent?: string;
  citations?: Citation[];
  isOptimistic?: boolean;
  tempId?: string;
  error?: string;
  isCancelled?: boolean;
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

export function getCitations(content: Content[] | string): Citation[] {
  if (typeof content === "string") {
    return [];
  }
  const citations: Citation[] = [];
  content.forEach((item) => {
    if (item.type === "text" && (item as TextContent).citations) {
      citations.push(...((item as TextContent).citations || []));
    }
  });
  return citations;
}

export function getMediaContent(
  content: Content[] | string
): (ImageContent | AudioContent | VideoContent)[] {
  if (typeof content === "string") {
    return [];
  }
  return content.filter(
    (item): item is ImageContent | AudioContent | VideoContent =>
      item.type === "image" || item.type === "audio" || item.type === "video"
  );
}

export function getImageContent(content: Content[] | string): ImageContent[] {
  if (typeof content === "string") {
    return [];
  }
  return content.filter((item): item is ImageContent => item.type === "image");
}

export function getAudioContent(content: Content[] | string): AudioContent[] {
  if (typeof content === "string") {
    return [];
  }
  return content.filter((item): item is AudioContent => item.type === "audio");
}

export function getVideoContent(content: Content[] | string): VideoContent[] {
  if (typeof content === "string") {
    return [];
  }
  return content.filter((item): item is VideoContent => item.type === "video");
}

/**
 * Parses an incoming message dates and returns a Message object
 * @param message - The incoming message
 * @returns A Message object
 */
function parseIncomingMessage(message: IncomingMessage): Message {
  return {
    ...message,
    id: message.id.replace(/^run-+/, ""),
    textContent: getTextContent(message.content),
    thinkingContent: getThinkingContent(message.content),
    citations: getCitations(message.content),
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
    addOptimisticMessage: (
      state,
      action: PayloadAction<{
        tempId: string;
        content: string;
        threadId: string;
        userId?: string;
      }>
    ) => {
      const { tempId, content, threadId, userId } = action.payload;
      const optimisticMessage: Message = {
        id: tempId,
        tempId,
        type: "human",
        content,
        thread_id: threadId,
        user_id: userId,
        created_at: Date.now(),
        textContent: content,
        isOptimistic: true,
      };

      state.messageIds.push(tempId);
      state.messageMap[tempId] = optimisticMessage;
    },
    markMessageFailed: (
      state,
      action: PayloadAction<{ tempId: string; error: string }>
    ) => {
      const { tempId, error } = action.payload;
      const message = state.messageMap[tempId];
      if (message) {
        message.error = error;
        message.isOptimistic = false;
      }
    },
    removeOptimisticMessage: (state, action: PayloadAction<string>) => {
      const tempId = action.payload;
      delete state.messageMap[tempId];
      state.messageIds = state.messageIds.filter((id) => id !== tempId);
    },
    markMessageCancelled: (state, action: PayloadAction<string>) => {
      const messageId = action.payload;
      const message = state.messageMap[messageId];
      if (message) {
        message.isCancelled = true;
      }
    },
    upsertMessage: (state, action: PayloadAction<IncomingMessageEvent>) => {
      const incomingMessage = action.payload.message;

      // Check if we have an optimistic message to replace
      const tempId = (incomingMessage as IncomingMessage & { temp_id?: string }).temp_id;
      if (tempId) {
        // Remove the optimistic message
        const optimisticIndex = state.messageIds.indexOf(tempId);
        if (optimisticIndex !== -1) {
          state.messageIds.splice(optimisticIndex, 1);
          delete state.messageMap[tempId];
        }
      }

      upsert(state, incomingMessage);
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
      const messageId = action.payload.message.id.replace(/^run-+/, "");
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
            ? existingMessage.textContent + (incomingTextContent || "")
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
            upsert(state, {
              ...message,
              created_at: message.created_at,
            } as IncomingMessage);
          }
        }
      );
  },
});

export const {
  addOptimisticMessage,
  markMessageFailed,
  removeOptimisticMessage,
  markMessageCancelled,
  upsertMessage,
  upsertMessages,
  partialMessage,
} = messagesSlice.actions;

// Base selectors
const selectMessagesState = (state: RootState) => state.messages;
const selectMessageIds = (state: RootState) => state.messages.messageIds;
const selectMessageMap = (state: RootState) => state.messages.messageMap;

// Memoized selectors
export const getMessagesLoading = createSelector(
  [selectMessagesState],
  (state) => state.loading
);

export const getMessagesError = createSelector(
  [selectMessagesState],
  (state) => state.error
);

// Update selector to return messages in order with memoization
export const getMessages = createSelector(
  [selectMessageIds, selectMessageMap],
  (messageIds, messageMap) => messageIds.map((id) => messageMap[id])
);

export const getMessage = createSelector(
  [selectMessageMap, (_, id: string) => id],
  (messageMap, id) => messageMap[id]
);

export const selectThreadMessages = createSelector(
  [getMessages, (_, threadId?: string) => threadId],
  (messages, threadId) =>
    messages.filter((message) => message.thread_id === threadId)
);

export default messagesSlice.reducer;
