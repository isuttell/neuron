import { configureStore, EnhancedStore } from "@reduxjs/toolkit";
import { fetchMessagesByThread } from "../../actions/messageActions";
import type { RootState } from "../../store";
import messagesReducer, {
  getMessage,
  getMessages,
  getMessagesError,
  getMessagesLoading,
  getTextContent,
  getThinkingContent,
  getCitations,
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
          textContent: mockMessage.content,
          thinkingContent: "",
          citations: [],
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

      it("should handle messages with double dash prefix", () => {
        const doubleDashMessage = {
          ...mockMessage,
          id: "run--789",
          content: "Double dash message",
        };

        store.dispatch(upsertMessage({ message: doubleDashMessage }));
        const state = store.getState().messages;

        expect(state.messageMap["789"]).toBeTruthy();
        expect(state.messageMap["789"].id).toBe("789");
        expect(state.messageIds).toContain("789");
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
        // The actual behavior directly concatenates the content without a newline
        expect(state.messageMap["123"].textContent).toBe(
          "Hello, world Updated"
        );
        expect(state.messageMap["123"].status).toBe("completed");
      });

      it("should update existing message content with array content", () => {
        // First create a message with array content
        const arrayContentMessage = {
          ...mockMessage,
          content: [{ type: "text", text: "Initial content", index: 0 }],
        };

        store.dispatch(upsertMessage({ message: arrayContentMessage }));

        // Then update it with more array content
        store.dispatch(
          partialMessage({
            message: {
              ...arrayContentMessage,
              content: [{ type: "text", text: "New content", index: 1 }],
              status: "completed",
              index: 1,
            },
          })
        );

        const state = store.getState().messages;
        // The actual implementation concatenates the text content directly
        // rather than merging the arrays
        expect(state.messageMap["123"].textContent).toBe(
          "Initial contentNew content"
        );
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
        const serializableError = { message: "Failed", type: "unknown" as const };
        store.dispatch(
          fetchMessagesByThread.rejected(null, "", "thread-1", serializableError)
        );
        const state = store.getState().messages;
        expect(state.loading).toBe(false);
        expect(state.error).toEqual(serializableError);
      });

      it("should set default error when rejected without message", () => {
        const serializableError = { message: "An unknown error occurred", type: "unknown" as const };
        store.dispatch(
          fetchMessagesByThread.rejected(null, "", "thread-1", serializableError)
        );
        const state = store.getState().messages;
        expect(state.loading).toBe(false);
        expect(state.error).toEqual(serializableError);
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

    describe("getThinkingContent", () => {
      it("should return empty string for string content", () => {
        expect(getThinkingContent("Hello")).toBe("");
      });

      it("should extract thinking content from array", () => {
        const content = [
          { type: "text", text: "Hello", index: 0 },
          { type: "thinking", thinking: "Reasoning about the answer", index: 1 },
        ];
        expect(getThinkingContent(content)).toBe("Reasoning about the answer");
      });

      it("should return undefined when no thinking content", () => {
        const content = [
          { type: "text", text: "Hello", index: 0 },
        ];
        expect(getThinkingContent(content)).toBeUndefined();
      });
    });

    describe("getCitations", () => {
      it("should return empty array for string content", () => {
        expect(getCitations("Hello")).toEqual([]);
      });

      it("should extract citations from text content", () => {
        const content = [
          {
            type: "text",
            text: "The grass is green",
            index: 0,
            citations: [
              {
                type: "char_location" as const,
                cited_text: "The grass is green.",
                document_index: 0,
                document_title: "My Document",
                start_char_index: 0,
                end_char_index: 20,
              },
            ],
          },
          { type: "text", text: "and the sky is blue", index: 1 },
        ];
        const citations = getCitations(content);
        expect(citations).toHaveLength(1);
        expect(citations[0].cited_text).toBe("The grass is green.");
      });

      it("should combine citations from multiple text blocks", () => {
        const content = [
          {
            type: "text",
            text: "The grass is green",
            index: 0,
            citations: [
              {
                type: "char_location" as const,
                cited_text: "The grass is green.",
                document_index: 0,
                document_title: "My Document",
                start_char_index: 0,
                end_char_index: 20,
              },
            ],
          },
          {
            type: "text",
            text: "and the sky is blue",
            index: 1,
            citations: [
              {
                type: "char_location" as const,
                cited_text: "The sky is blue.",
                document_index: 0,
                document_title: "My Document",
                start_char_index: 20,
                end_char_index: 36,
              },
            ],
          },
        ];
        const citations = getCitations(content);
        expect(citations).toHaveLength(2);
        expect(citations[0].cited_text).toBe("The grass is green.");
        expect(citations[1].cited_text).toBe("The sky is blue.");
      });

      it("should handle content without citations", () => {
        const content = [
          { type: "text", text: "Hello", index: 0 },
          { type: "thinking", thinking: "Thinking...", index: 1 },
        ];
        expect(getCitations(content)).toEqual([]);
      });
    });
  });

  describe("message with citations", () => {
    it("should parse message with citations correctly", () => {
      const messageWithCitations = {
        id: "run-789",
        type: "ai" as const,
        content: [
          {
            type: "text",
            text: "Based on the document, the grass is green",
            index: 0,
            citations: [
              {
                type: "char_location" as const,
                cited_text: "The grass is green.",
                document_index: 0,
                document_title: "My Document",
                start_char_index: 0,
                end_char_index: 20,
              },
            ],
          },
        ],
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

      store.dispatch(upsertMessage({ message: messageWithCitations }));
      const state = store.getState().messages;
      const message = state.messageMap["789"];

      expect(message.textContent).toBe("Based on the document, the grass is green");
      expect(message.citations).toHaveLength(1);
      expect(message.citations![0].cited_text).toBe("The grass is green.");
    });
  });
});
