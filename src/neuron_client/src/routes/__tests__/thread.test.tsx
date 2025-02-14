import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import Thread from "../thread";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import * as hooks from "../../hooks";

// Mock action creators
jest.mock("../../actions/messageActions", () => ({
  fetchMessagesByThread: jest.fn((threadId) => ({
    type: "messages/fetchMessagesByThread",
    payload: threadId,
  })),
  postMessageByThread: jest.fn((params) => ({
    type: "messages/postMessageByThread",
    payload: params,
  })),
}));

// Mock all the imported components
jest.mock("@/lib/loading", () => ({
  __esModule: true,
  default: () => (
    <div className="flex flex-1 items-center justify-center h-full">
      <div className="flex flex-col items-center gap-2">
        <svg
          role="progressbar"
          className="animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          width="64"
          height="64"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      </div>
    </div>
  ),
}));

jest.mock("../../messages/MessageForm", () => ({
  __esModule: true,
  default: () => <div data-testid="message-form">MessageForm</div>,
}));

jest.mock("../../messages/MessageItem", () => ({
  __esModule: true,
  default: ({
    messageId,
    showTools,
    onPromptClick,
  }: {
    messageId: string;
    showTools?: boolean;
    onPromptClick?: (prompt: string) => void;
  }) => {
    // Get message from test data
    const message = mockMessages.find((msg) => msg.id === messageId);
    if (!message) return null;

    // Filter system messages when showTools is false
    if (
      !showTools &&
      typeof message.node === "string" &&
      ["agent", "tools"].includes(message.node)
    ) {
      return null;
    }

    return (
      <div
        data-testid={`message-${messageId}`}
        onClick={() => onPromptClick?.("Test message")}
      >
        MessageItem {messageId}
      </div>
    );
  },
}));

jest.mock("../../components/MediaTimeline", () => ({
  __esModule: true,
  default: ({ threadId }: { threadId: string }) => (
    <div data-testid="media-timeline" className="flex flex-col h-full">
      MediaTimeline for thread {threadId}
    </div>
  ),
}));

jest.mock("@/components/ui/sidebar", () => ({
  __esModule: true,
  SidebarTrigger: () => (
    <button aria-label="Toggle Sidebar">Toggle Sidebar</button>
  ),
}));

jest.mock("@/personalities/EditPersonalityDialog", () => ({
  __esModule: true,
  default: () => (
    <button aria-label="Edit Personality">Edit Personality</button>
  ),
}));

jest.mock("@/components/DeleteThreadButton", () => ({
  __esModule: true,
  default: () => <button data-testid="delete-thread">Delete Thread</button>,
}));

jest.mock("@/components/ToggleSystemMessages", () => ({
  __esModule: true,
  default: ({
    showTools,
    onToggle,
  }: {
    showTools: boolean;
    onToggle: () => void;
  }) => (
    <button data-testid="toggle-system" onClick={onToggle}>
      {showTools ? "Hide" : "Show"} System Messages
    </button>
  ),
}));

jest.mock("@/components/MediaPanelWidth", () => ({
  __esModule: true,
  default: ({
    widthMode,
    onChange,
  }: {
    widthMode: string;
    onChange: (mode: "hidden" | "narrow") => void;
  }) => (
    <button
      data-testid="media-panel-width"
      onClick={() => {
        const newMode = widthMode === "hidden" ? "narrow" : "hidden";
        onChange(newMode);
        localStorage.setItem("widthMode", newMode);
      }}
    >
      Toggle Width
    </button>
  ),
}));

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: jest.fn((key: string) => store[key] || null),
  setItem: jest.fn((key: string, value: string) => {
    store[key] = value;
  }),
  clear: jest.fn(() => {
    Object.keys(store).forEach((key) => {
      delete store[key];
    });
  }),
};
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// Mock dispatch and selector hooks
const mockDispatch = jest.fn();
const useAppDispatchMock = jest.spyOn(hooks, "useAppDispatch");
useAppDispatchMock.mockReturnValue(mockDispatch);

interface Message {
  id: string;
  content: string | Array<{ type: string; text: string }>;
  type: "human" | "ai";
  thread_id: string;
  created_at: string;
  node?: string;
}

interface MediaItem {
  id: string;
  thread_id: string;
  created_at: string;
}

interface Thread {
  id: string;
  name: string;
  personality_id: string;
  message_count: number;
  context?: string;
  memory?: string;
  status?: string;
  created_at?: number;
  updated_at?: number;
}

interface Personality {
  id: string;
  name: string;
  system_prompt?: string;
  context?: string;
  memory?: string;
}

interface AppState {
  messages: {
    messageMap: Record<string, Message>;
    messageIds: string[];
    loading: boolean;
    error: null | string;
  };
  media: {
    items: MediaItem[];
  };
  threads: {
    threads: Thread[];
    loading: boolean;
    error: null | string;
  };
  personalities: {
    personalities: Personality[];
    activePersonalityId: string | null;
  };
}

// Mock messages data for MessageItem component
const mockMessages: Message[] = [
  {
    id: "msg-1",
    content: "Hello",
    type: "human",
    thread_id: "thread-1",
    created_at: "2024-02-04T12:00:00Z",
  },
  {
    id: "msg-2",
    content: "Hi there",
    type: "ai",
    thread_id: "thread-1",
    created_at: "2024-02-04T12:01:00Z",
  },
  {
    id: "msg-3",
    content: "System message",
    type: "ai",
    node: "tools",
    thread_id: "thread-1",
    created_at: "2024-02-04T12:02:00Z",
  },
];

const mockMediaItems: MediaItem[] = [
  {
    id: "media-1",
    thread_id: "thread-1",
    created_at: "2024-02-04T12:00:00Z",
  },
];

describe("Thread", () => {
  const mockThread: Thread = {
    id: "thread-1",
    name: "Test Thread",
    personality_id: "personality-1",
    message_count: 2,
  };

  let originalScrollIntoView: typeof window.HTMLElement.prototype.scrollIntoView;
  let mockScrollIntoView: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    mockScrollIntoView = jest.fn();
    originalScrollIntoView = window.HTMLElement.prototype.scrollIntoView;
    window.HTMLElement.prototype.scrollIntoView = mockScrollIntoView;
  });

  afterEach(() => {
    window.HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
  });

  const renderThread = (
    initialState: Partial<AppState> = {
      messages: {
        messageMap: {},
        messageIds: [],
        loading: false,
        error: null,
      },
      media: {
        items: [],
      },
      threads: {
        threads: [mockThread],
        loading: false,
        error: null,
      },
      personalities: {
        personalities: [],
        activePersonalityId: null,
      },
    }
  ) => {
    const store = configureStore({
      reducer: {
        messages: (state = initialState.messages!) => state,
        media: (state = initialState.media!) => state,
        threads: (state = initialState.threads!) => state,
        personalities: (state = initialState.personalities!) => state,
      },
    });

    return render(
      <Provider store={store}>
        <MemoryRouter initialEntries={["/thread/thread-1"]}>
          <Routes>
            <Route
              path="/thread/:threadId"
              element={
                <MediaPlayerProvider>
                  <Thread />
                </MediaPlayerProvider>
              }
            />
          </Routes>
        </MemoryRouter>
      </Provider>
    );
  };

  describe("Initial Rendering", () => {
    it("should show loading state when loading messages", () => {
      const initialState: Partial<AppState> = {
        messages: {
          messageMap: {},
          messageIds: [],
          loading: true,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: { personalities: [], activePersonalityId: null },
      };

      renderThread(initialState);
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("should show thread name in header", () => {
      renderThread();
      expect(screen.getByText(mockThread.name)).toBeInTheDocument();
    });

    it("should fetch messages on mount", () => {
      renderThread();
      expect(mockDispatch).toHaveBeenCalledWith({
        type: "messages/fetchMessagesByThread",
        payload: "thread-1",
      });
    });

    it("should show 'No messages' when thread is empty", () => {
      const emptyThread = {
        ...mockThread,
        message_count: 0,
      };
      const initialState: Partial<AppState> = {
        messages: {
          messageMap: {},
          messageIds: [],
          loading: false,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [emptyThread], loading: false, error: null },
        personalities: { personalities: [], activePersonalityId: null },
      };

      renderThread(initialState);
      expect(screen.getByText(/no messages/i)).toBeInTheDocument();
    });
  });

  describe("Message Handling", () => {
    it("should handle array content in messages", () => {
      const messagesWithArray = [
        {
          id: "msg-1",
          content: [
            { type: "text", text: "First part" },
            { type: "text", text: "Second part" },
          ],
          type: "ai",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:00:00Z",
        },
      ];

      const initialState: Partial<AppState> = {
        messages: {
          messageMap: messagesWithArray.reduce(
            (acc, msg) => ({ ...acc, [msg.id]: msg }),
            {}
          ),
          messageIds: messagesWithArray.map((msg) => msg.id),
          loading: false,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: { personalities: [], activePersonalityId: null },
      };

      renderThread(initialState);
      expect(screen.getByTestId("message-msg-1")).toBeInTheDocument();
    });

    it("should filter system messages when showTools is false", async () => {
      const initialState: Partial<AppState> = {
        messages: {
          messageMap: mockMessages.reduce(
            (acc, msg) => ({ ...acc, [msg.id]: msg }),
            {}
          ),
          messageIds: mockMessages.map((msg) => msg.id),
          loading: false,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: { personalities: [], activePersonalityId: null },
      };

      renderThread(initialState);

      // Initially system messages should be hidden
      expect(screen.queryByTestId("message-msg-3")).not.toBeInTheDocument();

      // Toggle system messages
      fireEvent.click(screen.getByTestId("toggle-system"));

      // Now system message should be visible
      await waitFor(() => {
        expect(screen.getByTestId("message-msg-3")).toBeInTheDocument();
      });
    });

    it("should handle message submission", async () => {
      const initialState: Partial<AppState> = {
        messages: {
          messageMap: mockMessages.reduce(
            (acc, msg) => ({ ...acc, [msg.id]: msg }),
            {}
          ),
          messageIds: mockMessages.map((msg) => msg.id),
          loading: false,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: {
          personalities: [],
          activePersonalityId: null,
        },
      };

      renderThread(initialState);

      // Get the onPromptClick prop from MessageItem
      const messageItem = screen.getByTestId("message-msg-1");
      const prompt = "Test message";

      // Simulate clicking a prompt
      fireEvent.click(messageItem);

      // Wait for debounced function to be called
      await waitFor(() => {
        expect(mockDispatch).toHaveBeenCalledWith({
          type: "messages/postMessageByThread",
          payload: {
            threadId: mockThread.id,
            prompt,
            personalityId: mockThread.personality_id,
          },
        });
      });
    });

    it("should scroll to last user message", async () => {
      const messagesWithMultipleUsers = [
        {
          id: "msg-1",
          content: "First message",
          type: "human",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:00:00Z",
        },
        {
          id: "msg-2",
          content: "AI response",
          type: "ai",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:01:00Z",
        },
        {
          id: "msg-3",
          content: "Last user message",
          type: "human",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:02:00Z",
        },
      ];

      const initialState: Partial<AppState> = {
        messages: {
          messageMap: messagesWithMultipleUsers.reduce(
            (acc, msg) => ({ ...acc, [msg.id]: msg }),
            {}
          ),
          messageIds: messagesWithMultipleUsers.map((msg) => msg.id),
          loading: false,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: { personalities: [], activePersonalityId: null },
      };

      renderThread(initialState);

      // Wait for the setTimeout in useEffect
      await new Promise((resolve) => setTimeout(resolve, 0));
      expect(mockScrollIntoView).toHaveBeenCalledWith({
        behavior: "instant",
        block: "start",
      });
    });
  });

  describe("Media Panel", () => {
    beforeEach(() => {
      localStorageMock.clear();
    });

    it("should toggle media panel width", () => {
      const initialState: Partial<AppState> = {
        messages: {
          messageMap: {},
          messageIds: [],
          loading: false,
          error: null,
        },
        media: { items: mockMediaItems },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: { personalities: [], activePersonalityId: null },
      };

      renderThread(initialState);

      const widthToggle = screen.getByTestId("media-panel-width");

      // Initially hidden
      const initialPanel = screen.getByRole("complementary");
      expect(initialPanel).toHaveClass("hidden");
      expect(screen.queryByTestId("media-timeline")).not.toBeInTheDocument();

      // Toggle to narrow
      fireEvent.click(widthToggle);
      const mediaPanel = screen.getByRole("complementary");
      expect(mediaPanel).toHaveClass("max-w-[512px]", "w-1/4");
      expect(screen.getByTestId("media-timeline")).toBeInTheDocument();

      // Toggle back to hidden
      fireEvent.click(widthToggle);
      expect(mediaPanel).toHaveClass("hidden");
      expect(screen.queryByTestId("media-timeline")).not.toBeInTheDocument();
    });

    it("should persist width mode in localStorage", async () => {
      renderThread();

      const widthToggle = screen.getByTestId("media-panel-width");
      fireEvent.click(widthToggle);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "widthMode",
        "narrow"
      );
      expect(store["widthMode"]).toBe("narrow");
    });
  });

  describe("UI Components", () => {
    it("should render sidebar trigger", () => {
      renderThread();
      expect(
        screen.getByRole("button", { name: /toggle sidebar/i })
      ).toBeInTheDocument();
    });

    it("should render edit personality dialog when active personality exists", () => {
      const mockPersonality: Personality = {
        id: "personality-1",
        name: "Test Personality",
      };

      const initialState: Partial<AppState> = {
        messages: {
          messageMap: {},
          messageIds: [],
          loading: false,
          error: null,
        },
        media: { items: [] },
        threads: { threads: [mockThread], loading: false, error: null },
        personalities: {
          personalities: [mockPersonality],
          activePersonalityId: "personality-1",
        },
      };

      renderThread(initialState);
      expect(
        screen.getByRole("button", { name: /edit personality/i })
      ).toBeInTheDocument();
    });
  });
});
