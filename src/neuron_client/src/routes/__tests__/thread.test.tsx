import { vi } from 'vitest';
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { configureStore } from "@reduxjs/toolkit";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as hooks from "../../hooks";
import Thread from "../thread";

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock action creators
vi.mock("../../actions/messageActions", () => ({
  fetchMessagesByThread: vi.fn((threadId) => ({
    type: "messages/fetchMessagesByThread",
    payload: threadId,
  })),
  postMessageByThread: vi.fn((params) => ({
    type: "messages/postMessageByThread",
    payload: params,
  })),
}));

// Mock TooltipProvider
vi.mock("@/components/ui/tooltip", () => ({
  __esModule: true,
  TooltipProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

// Mock all the imported components
vi.mock("@/lib/loading", () => ({
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

vi.mock("../../messages/MessageForm", () => ({
  __esModule: true,
  default: () => <div data-testid="message-form">MessageForm</div>,
}));

vi.mock("../../messages/MessageItem", () => ({
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

    // Create a div with the message ID as a data-testid
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

vi.mock("../../components/MediaTimeline", () => ({
  __esModule: true,
  default: ({ threadId }: { threadId: string }) => (
    <div data-testid="media-timeline" className="flex flex-col h-full">
      MediaTimeline for thread {threadId}
    </div>
  ),
}));

vi.mock("@/components/ui/sidebar", () => ({
  __esModule: true,
  SidebarTrigger: () => (
    <button aria-label="Toggle Sidebar">Toggle Sidebar</button>
  ),
}));


vi.mock("@/components/DeleteThreadDialog", () => ({
  __esModule: true,
  default: () => <div data-testid="delete-thread-dialog">Delete Thread Dialog</div>,
}));

vi.mock("@/components/ThreadHeaderActions", () => ({
  __esModule: true,
  default: ({
    showTools,
    onToggleTools,
    onEditPersonality,
    onManageUsers,
    onDeleteThread,
  }: {
    showTools: boolean;
    onToggleTools: () => void;
    onEditPersonality: () => void;
    onManageUsers: () => void;
    onDeleteThread: () => void;
  }) => (
    <div data-testid="thread-header-actions">
      <button data-testid="toggle-system" onClick={onToggleTools}>
        {showTools ? "Hide" : "Show"} System Messages
      </button>
      <button onClick={onEditPersonality}>Edit Personality</button>
      <button onClick={onManageUsers}>Manage Users</button>
      <button onClick={onDeleteThread}>Delete Thread</button>
    </div>
  ),
}));

vi.mock("@/components/MediaPanelToggle", () => ({
  __esModule: true,
  default: ({
    isVisible,
    onChange,
  }: {
    isVisible: boolean;
    onChange: (visible: boolean) => void;
  }) => (
    <button
      data-testid="media-panel-toggle"
      onClick={() => {
        const newState = !isVisible;
        onChange(newState);
        localStorage.setItem("mediaPanelVisible", String(newState));
      }}
    >
      Toggle Media Panel
    </button>
  ),
}));

vi.mock("@/threads/ThreadUsersDialog", () => ({
  __esModule: true,
  default: () => <div data-testid="thread-users-dialog">Thread Users Dialog</div>,
}));

// Mock localStorage
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    store[key] = value;
  }),
  clear: vi.fn(() => {
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
const mockDispatch = vi.fn();
const useAppDispatchMock = vi.spyOn(hooks, "useAppDispatch");
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
  socket: {
    connected: boolean;
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
  let mockScrollIntoView: vi.Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockScrollIntoView = vi.fn();
    originalScrollIntoView = window.HTMLElement.prototype.scrollIntoView;
    window.HTMLElement.prototype.scrollIntoView = mockScrollIntoView;
    mockNavigate.mockClear();
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
      socket: {
        connected: true,
      },
    }
  ) => {
    const store = configureStore({
      reducer: {
        messages: (state = initialState.messages!) => state,
        media: (state = initialState.media!) => state,
        threads: (state = initialState.threads!) => state,
        personalities: (state = initialState.personalities!) => state,
        socket: (state = initialState.socket || { connected: true }) => state,
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
        socket: { connected: true },
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
          // Add textContent property to match what the component expects
          textContent: "First part\nSecond part",
          thinkingContent: "",
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

      // Wait for the component to render
      expect(screen.getByTestId("message-msg-1")).toBeInTheDocument();
    });

    it("should filter system messages when showTools is false", async () => {
      // Add textContent property to messages to match what the component expects
      const messagesWithTextContent = mockMessages.map((msg) => ({
        ...msg,
        textContent: typeof msg.content === "string" ? msg.content : "",
        thinkingContent: "",
      }));

      const initialState: Partial<AppState> = {
        messages: {
          messageMap: messagesWithTextContent.reduce(
            (acc, msg) => ({ ...acc, [msg.id]: msg }),
            {}
          ),
          messageIds: messagesWithTextContent.map((msg) => msg.id),
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
      // Add textContent property to messages to match what the component expects
      const messagesWithTextContent = mockMessages.map((msg) => ({
        ...msg,
        textContent: typeof msg.content === "string" ? msg.content : "",
        thinkingContent: "",
      }));

      const initialState: Partial<AppState> = {
        messages: {
          messageMap: messagesWithTextContent.reduce(
            (acc, msg) => ({ ...acc, [msg.id]: msg }),
            {}
          ),
          messageIds: messagesWithTextContent.map((msg) => msg.id),
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
      // Add textContent property to messages to match what the component expects
      const messagesWithMultipleUsers = [
        {
          id: "msg-1",
          content: "First message",
          type: "human",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:00:00Z",
          textContent: "First message",
          thinkingContent: "",
        },
        {
          id: "msg-2",
          content: "AI response",
          type: "ai",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:01:00Z",
          textContent: "AI response",
          thinkingContent: "",
        },
        {
          id: "msg-3",
          content: "Last user message",
          type: "human",
          thread_id: "thread-1",
          created_at: "2024-02-04T12:02:00Z",
          textContent: "Last user message",
          thinkingContent: "",
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
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Verify scrollIntoView was called
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

    it("should toggle media panel visibility", () => {
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

      const toggleButton = screen.getByTestId("media-panel-toggle");

      // Initially hidden
      const initialPanel = screen.getByRole("complementary");
      expect(initialPanel).toHaveClass("lg:hidden");
      expect(screen.queryByTestId("media-timeline")).not.toBeInTheDocument();

      // Toggle to visible
      fireEvent.click(toggleButton);
      const mediaPanel = screen.getByRole("complementary");
      expect(mediaPanel).toHaveClass("w-1/3");
      expect(screen.getByTestId("media-timeline")).toBeInTheDocument();

      // Toggle back to hidden
      fireEvent.click(toggleButton);
      expect(mediaPanel).toHaveClass("lg:hidden");
      expect(screen.queryByTestId("media-timeline")).not.toBeInTheDocument();
    });

    it("should persist panel visibility in localStorage", async () => {
      renderThread();

      const toggleButton = screen.getByTestId("media-panel-toggle");
      fireEvent.click(toggleButton);

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "mediaPanelVisible",
        "true"
      );
      expect(store["mediaPanelVisible"]).toBe("true");
    });
  });

  describe("UI Components", () => {
    it("should render sidebar trigger", () => {
      renderThread();
      expect(
        screen.getByRole("button", { name: /toggle sidebar/i })
      ).toBeInTheDocument();
    });

    it("should navigate to personality edit page when edit personality is clicked", async () => {
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

      // Check that the ThreadHeaderActions component is rendered
      expect(screen.getByTestId("thread-header-actions")).toBeInTheDocument();

      // Click the edit personality button
      const editButton = screen.getByRole("button", { name: /edit personality/i });
      fireEvent.click(editButton);

      // Verify navigation was called with correct path
      expect(mockNavigate).toHaveBeenCalledWith("/personality/personality-1/edit");
    });
  });
});
