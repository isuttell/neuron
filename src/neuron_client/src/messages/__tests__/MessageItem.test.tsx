import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import MessageItem from "../MessageItem";
import messagesReducer, { upsertMessage } from "@/slices/messagesSlice";
import usersReducer from "@/slices/usersSlice";
import { Citation } from "@/slices/messagesSlice";
import { TooltipProvider } from "@/components/ui/tooltip";

// Mock the Citations component
jest.mock("../Citations", () => ({
  __esModule: true,
  default: ({ citations }: { citations: Citation[] }) => (
    <div data-testid="citations-component">
      Citations: {citations.length}
    </div>
  ),
}));

// Mock the Content component to avoid react-markdown issues
jest.mock("../Content", () => ({
  __esModule: true,
  default: ({ content }: { content: string }) => (
    <div>{content}</div>
  ),
}));

describe("MessageItem", () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        messages: messagesReducer,
        users: usersReducer,
      },
    });
  });

  const renderWithStore = (component: React.ReactElement) => {
    return render(
      <Provider store={store}>
        <TooltipProvider>{component}</TooltipProvider>
      </Provider>
    );
  };

  it("should render a basic AI message", () => {
    const message = {
      id: "123",
      type: "ai" as const,
      content: "Hello, I am an AI assistant",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="123" />);

    expect(screen.getByText("Hello, I am an AI assistant")).toBeInTheDocument();
  });

  it("should render a human message", () => {
    const message = {
      id: "456",
      type: "human" as const,
      content: "Hello AI",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="456" />);

    expect(screen.getByText("Hello AI")).toBeInTheDocument();
  });

  it("should render citations when present", () => {
    const message = {
      id: "789",
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
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="789" />);

    expect(screen.getByText("Based on the document, the grass is green")).toBeInTheDocument();
    expect(screen.getByTestId("citations-component")).toBeInTheDocument();
    expect(screen.getByText("Citations: 1")).toBeInTheDocument();
  });

  it("should not render citations when empty", () => {
    const message = {
      id: "101",
      type: "ai" as const,
      content: "No citations here",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="101" />);

    expect(screen.getByText("No citations here")).toBeInTheDocument();
    expect(screen.queryByTestId("citations-component")).not.toBeInTheDocument();
  });

  it("should render thinking content", () => {
    const message = {
      id: "102",
      type: "ai" as const,
      content: [
        { type: "thinking", thinking: "Let me think about this...", index: 0 },
        { type: "text", text: "Here's my answer", index: 1 },
      ],
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="102" />);

    expect(screen.getByText("Thoughts")).toBeInTheDocument();
    expect(screen.getByText("Here's my answer")).toBeInTheDocument();
  });

  it("should handle tool messages", () => {
    const message = {
      id: "103",
      type: "tool" as const,
      name: "calculator",
      content: "Result: 42",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="103" showTools={true} />);

    expect(screen.getByText("Result: 42")).toBeInTheDocument();
  });

  it("should hide tool messages when showTools is false", () => {
    const message = {
      id: "104",
      type: "tool" as const,
      name: "hidden_tool",
      content: "This should be hidden",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    const { container } = renderWithStore(<MessageItem messageId="104" showTools={false} />);

    // Tool messages return an empty div when showTools is false
    expect(container.querySelector('div')).toBeEmptyDOMElement();
    expect(screen.queryByText("This should be hidden")).not.toBeInTheDocument();
  });

  it("should render message with multiple citations", () => {
    const message = {
      id: "105",
      type: "ai" as const,
      content: [
        {
          type: "text",
          text: "The grass is green",
          index: 0,
          citations: [
            {
              type: "char_location" as const,
              cited_text: "The grass is green.",
              document_index: 0,
              document_title: "Doc 1",
              start_char_index: 0,
              end_char_index: 20,
            },
          ],
        },
        {
          type: "text",
          text: " and the sky is blue",
          index: 1,
          citations: [
            {
              type: "char_location" as const,
              cited_text: "The sky is blue.",
              document_index: 1,
              document_title: "Doc 2",
              start_char_index: 0,
              end_char_index: 16,
            },
          ],
        },
      ],
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="105" />);

    // The Content mock just renders the text content as a single line
    expect(screen.getByText(/The grass is green.*and the sky is blue/)).toBeInTheDocument();
    expect(screen.getByTestId("citations-component")).toBeInTheDocument();
    expect(screen.getByText("Citations: 2")).toBeInTheDocument();
  });

  it("should display token count when available", () => {
    const message = {
      id: "106",
      type: "ai" as const,
      content: "Message with tokens",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
      usage_metadata: {
        input_tokens: 10,
        output_tokens: 5,
        total_tokens: 15,
      },
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="106" />);

    expect(screen.getByText("15")).toBeInTheDocument();
  });

  it("should handle prompt click", () => {
    const mockOnPromptClick = jest.fn();
    const message = {
      id: "107",
      type: "ai" as const,
      content: "Click this prompt",
      thread_id: "thread-1",
      created_at: new Date().toISOString(),
    };

    store.dispatch(upsertMessage({ message }));
    renderWithStore(<MessageItem messageId="107" onPromptClick={mockOnPromptClick} />);

    expect(screen.getByText("Click this prompt")).toBeInTheDocument();
  });
});
