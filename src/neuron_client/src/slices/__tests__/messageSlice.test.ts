import { configureStore, EnhancedStore } from "@reduxjs/toolkit";
import { fetchMessagesByThread } from "../../actions/messageActions";
import type { RootState } from "../../store";
import messagesReducer, {
  getMessage,
  getMessages,
  getMessagesError,
  getMessagesLoading,
  getTextContent,
  partialMessage,
  selectThreadMessages,
  upsertMessage,
  upsertMessages,
} from "../messagesSlice";

describe("messageSlice", () => {
  let store: EnhancedStore<{
    messages: ReturnType<typeof messagesReducer>;
  }>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        messages: messagesReducer,
      },
    });
  });

  describe("initial state", () => {
    it("should have empty messageMap", () => {
      const state = store.getState().messages;
      expect(state.messageMap).toEqual({});
    });

    it("should have empty messageIds array", () => {
      const state = store.getState().messages;
      expect(state.messageIds).toEqual([]);
    });

    it("should have loading set to false", () => {
      const state = store.getState().messages;
      expect(state.loading).toBe(false);
    });

    it("should have error set to null", () => {
      const state = store.getState().messages;
      expect(state.error).toBeNull();
    });
  });

  describe("reducers", () => {
    const mockMessage = {
      id: "run-123",
      type: "ai" as const,
      content: "Hello, world",
      thread_id: "thread-1",
      created_at: "2024-02-04T12:00:00Z",
      name: undefined,
      status: undefined,
      tool_calls: undefined,
      tool_call_id: undefined,
      additional_kwargs: undefined,
      response_metadata: undefined,
      usage_metadata: undefined,
      node: undefined,
    };

    describe("upsertMessage", () => {
      it("should add a new message", () => {
        store.dispatch(upsertMessage({ message: mockMessage }));
        const state = store.getState().messages;

        expect(state.messageMap["123"]).toEqual({
          ...mockMessage,
          id: "123",
          created_at: new Date(mockMessage.created_at).getTime(),
        });
        expect(state.messageIds).toContain("123");
      });

      it("should update an existing message", () => {
        const updatedMessage = {
          ...mockMessage,
          content: "Updated content",
        };

        store.dispatch(upsertMessage({ message: mockMessage }));
        store.dispatch(upsertMessage({ message: updatedMessage }));

        const state = store.getState().messages;
        expect(state.messageMap["123"].content).toBe("Updated content");
        expect(state.messageIds.length).toBe(1);
      });
    });

    describe("upsertMessages", () => {
      it("should add multiple messages", () => {
        const messages = [
          mockMessage,
          {
            ...mockMessage,
            id: "run-456",
            content: "Second message",
          },
        ];

        store.dispatch(upsertMessages({ messages }));
        const state = store.getState().messages;

        expect(Object.keys(state.messageMap)).toHaveLength(2);
        expect(state.messageIds).toHaveLength(2);
        expect(state.messageMap["123"]).toBeTruthy();
        expect(state.messageMap["456"]).toBeTruthy();
      });
    });

    describe("partialMessage", () => {
      it("should update existing message content with string content", () => {
        store.dispatch(upsertMessage({ message: mockMessage }));
        store.dispatch(
          partialMessage({
            message: {
              ...mockMessage,
              content: " Updated",
              status: "completed",
              index: 1,
            },
          })
        );

        const state = store.getState().messages;
        expect(state.messageMap["123"].content).toBe("Hello, world Updated");
        expect(state.messageMap["123"].status).toBe("completed");
      });

      it("should update existing message content with array content", () => {
        store.dispatch(upsertMessage({ message: mockMessage }));
        store.dispatch(
          partialMessage({
            message: {
              ...mockMessage,
              content: [{ type: "text", text: "New content", index: 0 }],
              status: "completed",
              index: 1,
            },
          })
        );

        const state = store.getState().messages;
        expect(state.messageMap["123"].content).toEqual([
          { type: "text", text: "New content", index: 0 },
        ]);
        expect(state.messageMap["123"].status).toBe("completed");
      });

      it("should create new message if not exists", () => {
        store.dispatch(
          partialMessage({
            message: {
              ...mockMessage,
              status: "in_progress",
              index: 0,
            },
          })
        );

        const state = store.getState().messages;
        expect(state.messageMap["123"]).toBeTruthy();
        expect(state.messageMap["123"].status).toBe("in_progress");
      });
    });
  });

  describe("async thunks", () => {
    describe("fetchMessagesByThread", () => {
      it("should set loading true when pending", () => {
        store.dispatch(fetchMessagesByThread.pending("", "thread-1"));
        const state = store.getState().messages;
        expect(state.loading).toBe(true);
        expect(state.error).toBeNull();
      });

      it("should set error when rejected with message", () => {
        store.dispatch(
          fetchMessagesByThread.rejected(new Error("Failed"), "", "thread-1")
        );
        const state = store.getState().messages;
        expect(state.loading).toBe(false);
        expect(state.error).toBe("Failed");
      });

      it("should set default error when rejected without message", () => {
        store.dispatch(
          fetchMessagesByThread.rejected(new Error(), "", "thread-1")
        );
        const state = store.getState().messages;
        expect(state.loading).toBe(false);
        expect(state.error).toBe("Failed to fetch messages");
      });

      it("should update messages when fulfilled", () => {
        const messages = [
          {
            id: "run-123",
            type: "ai" as const,
            content: "Hello",
            thread_id: "thread-1",
            created_at: "2024-02-04T12:00:00Z",
            name: undefined,
            status: undefined,
            tool_calls: undefined,
            tool_call_id: undefined,
            additional_kwargs: undefined,
            response_metadata: undefined,
            usage_metadata: undefined,
            node: undefined,
          },
        ];

        store.dispatch(
          fetchMessagesByThread.fulfilled(
            { messages, media: [] },
            "",
            "thread-1"
          )
        );

        const state = store.getState().messages;
        expect(state.loading).toBe(false);
        expect(state.messageMap["123"]).toBeTruthy();
        expect(state.messageIds).toContain("123");
      });
    });
  });

  describe("selectors", () => {
    const mockMessages = [
      {
        id: "run-123",
        type: "ai" as const,
        content: "Message 1",
        thread_id: "thread-1",
        created_at: "2024-02-04T12:00:00Z",
        name: undefined,
        status: undefined,
        tool_calls: undefined,
        tool_call_id: undefined,
        additional_kwargs: undefined,
        response_metadata: undefined,
        usage_metadata: undefined,
        node: undefined,
      },
      {
        id: "run-456",
        type: "human" as const,
        content: "Message 2",
        thread_id: "thread-2",
        created_at: "2024-02-04T12:01:00Z",
        name: undefined,
        status: undefined,
        tool_calls: undefined,
        tool_call_id: undefined,
        additional_kwargs: undefined,
        response_metadata: undefined,
        usage_metadata: undefined,
        node: undefined,
      },
    ];

    beforeEach(() => {
      store.dispatch(upsertMessages({ messages: mockMessages }));
    });

    it("should select all messages in order", () => {
      const messages = getMessages(store.getState() as RootState);
      expect(messages).toHaveLength(2);
      expect(messages[0].id).toBe("123");
      expect(messages[1].id).toBe("456");
    });

    it("should select message by id", () => {
      const message = getMessage(store.getState() as RootState, "123");
      expect(message).toBeTruthy();
      expect(message?.content).toBe("Message 1");
    });

    it("should select messages by thread", () => {
      const messages = selectThreadMessages(
        store.getState() as RootState,
        "thread-1"
      );
      expect(messages).toHaveLength(1);
      expect(messages[0].thread_id).toBe("thread-1");
    });

    it("should get loading state", () => {
      const loading = getMessagesLoading(store.getState() as RootState);
      expect(loading).toBe(false);
    });

    it("should get error state", () => {
      const error = getMessagesError(store.getState() as RootState);
      expect(error).toBeNull();
    });
  });

  describe("utility functions", () => {
    describe("getTextContent", () => {
      it("should return string content directly", () => {
        const content = "Hello, world";
        expect(getTextContent(content)).toBe(content);
      });

      it("should join text content from array", () => {
        const content = [
          { type: "text", text: "Hello", index: 0 },
          { type: "text", text: "world", index: 1 },
        ];
        expect(getTextContent(content)).toBe("Hello\nworld");
      });

      it("should filter non-text content", () => {
        const content = [
          { type: "text", text: "Hello", index: 0 },
          { type: "image", text: "image.jpg", index: 1 },
          { type: "text", text: "world", index: 2 },
        ];
        expect(getTextContent(content)).toBe("Hello\nworld");
      });
    });
  });
});
