import messagesReducer, {
  addOptimisticMessage,
  markMessageFailed,
  removeOptimisticMessage,
  upsertMessage,
  IncomingMessage,
  Message,
} from "../messagesSlice";
import { configureStore } from "@reduxjs/toolkit";

// Type for our test store
type TestStore = ReturnType<typeof configureStore<{
  messages: ReturnType<typeof messagesReducer>;
}>>;

// Extended type for incoming messages with temp_id
interface IncomingMessageWithTempId extends IncomingMessage {
  temp_id?: string;
}

// Helper to get messages from test store
const getTestMessages = (state: { messages: ReturnType<typeof messagesReducer> }): Message[] => {
  const { messageIds, messageMap } = state.messages;
  return messageIds.map(id => messageMap[id]);
}

describe("messagesSlice - Optimistic Updates", () => {
  let store: TestStore;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        messages: messagesReducer,
      },
    });
  });

  describe("addOptimisticMessage", () => {
    it("should add an optimistic message to the store", () => {
      const tempId = "temp-123";
      const content = "Hello, world!";
      const threadId = "thread-123";
      const userId = "user-123";

      store.dispatch(
        addOptimisticMessage({
          tempId,
          content,
          threadId,
          userId,
        })
      );

      const state = store.getState();
      const messages = getTestMessages(state);
      expect(messages).toHaveLength(1);

      const message = messages[0];
      expect(message.id).toBe(tempId);
      expect(message.tempId).toBe(tempId);
      expect(message.content).toBe(content);
      expect(message.thread_id).toBe(threadId);
      expect(message.user_id).toBe(userId);
      expect(message.type).toBe("human");
      expect(message.isOptimistic).toBe(true);
      expect(message.created_at).toBeDefined();
    });
  });

  describe("markMessageFailed", () => {
    it("should mark an optimistic message as failed", () => {
      const tempId = "temp-123";
      const errorMessage = "Network error";

      // First add an optimistic message
      store.dispatch(
        addOptimisticMessage({
          tempId,
          content: "Test message",
          threadId: "thread-123",
        })
      );

      // Then mark it as failed
      store.dispatch(
        markMessageFailed({
          tempId,
          error: errorMessage,
        })
      );

      const state = store.getState();
      const messages = getTestMessages(state);
      const message = messages[0];
      expect(message.error).toBe(errorMessage);
      expect(message.isOptimistic).toBe(false);
    });
  });

  describe("removeOptimisticMessage", () => {
    it("should remove an optimistic message from the store", () => {
      const tempId = "temp-123";

      // Add an optimistic message
      store.dispatch(
        addOptimisticMessage({
          tempId,
          content: "Test message",
          threadId: "thread-123",
        })
      );

      const state1 = store.getState();
      expect(getTestMessages(state1)).toHaveLength(1);

      // Remove it
      store.dispatch(removeOptimisticMessage(tempId));

      const state2 = store.getState();
      expect(getTestMessages(state2)).toHaveLength(0);
    });
  });

  describe("upsertMessage with temp_id", () => {
    it("should replace an optimistic message when receiving the real message", () => {
      const tempId = "temp-123";
      const realId = "real-message-id";

      // Add an optimistic message
      store.dispatch(
        addOptimisticMessage({
          tempId,
          content: "Test message",
          threadId: "thread-123",
        })
      );

      // Receive the real message with temp_id
      store.dispatch(
        upsertMessage({
          message: {
            id: realId,
            temp_id: tempId,
            type: "human",
            content: "Test message",
            thread_id: "thread-123",
            created_at: new Date().toISOString(),
          } as IncomingMessageWithTempId,
        })
      );

      const state = store.getState();
      const messages = getTestMessages(state);
      expect(messages).toHaveLength(1);

      const message = messages[0];
      expect(message.id).toBe(realId);
      expect(message.tempId).toBeUndefined(); // Original tempId should not be preserved
      expect(message.isOptimistic).toBeUndefined(); // Should not be optimistic anymore
      expect(message.error).toBeUndefined(); // Should not have error
    });

    it("should handle upsertMessage without temp_id normally", () => {
      const messageId = "message-123";

      store.dispatch(
        upsertMessage({
          message: {
            id: messageId,
            type: "ai",
            content: "AI response",
            thread_id: "thread-123",
            created_at: new Date().toISOString(),
          },
        })
      );

      const state = store.getState();
      const messages = getTestMessages(state);
      expect(messages).toHaveLength(1);
      expect(messages[0].id).toBe(messageId);
    });
  });

  describe("Integration test", () => {
    it("should handle the full optimistic update flow", () => {
      const tempId = "temp-456";
      const realId = "real-456";
      const threadId = "thread-789";
      const content = "How's the weather?";

      // 1. User sends a message (optimistic)
      store.dispatch(
        addOptimisticMessage({
          tempId,
          content,
          threadId,
        })
      );

      let state = store.getState();
      let messages = getTestMessages(state);
      expect(messages).toHaveLength(1);
      expect(messages[0].isOptimistic).toBe(true);

      // 2. Server responds with the real message
      store.dispatch(
        upsertMessage({
          message: {
            id: realId,
            temp_id: tempId,
            type: "human",
            content,
            thread_id: threadId,
            created_at: new Date().toISOString(),
          } as IncomingMessageWithTempId,
        })
      );

      state = store.getState();
      messages = getTestMessages(state);
      expect(messages).toHaveLength(1);
      expect(messages[0].id).toBe(realId);
      expect(messages[0].isOptimistic).toBeUndefined();

      // 3. AI responds
      store.dispatch(
        upsertMessage({
          message: {
            id: "ai-response-123",
            type: "ai",
            content: "The weather is sunny!",
            thread_id: threadId,
            created_at: new Date().toISOString(),
          },
        })
      );

      state = store.getState();
      messages = getTestMessages(state);
      expect(messages).toHaveLength(2);
      expect(messages[1].type).toBe("ai");
    });
  });
});
