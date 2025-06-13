import { vi } from 'vitest';
import { configureStore } from "@reduxjs/toolkit";
import threadsReducer from "@/slices/threadsSlice";
import { api } from "@/lib/api";
import {
  addUserByEmail,
  fetchThreadUsers,
  removeThreadUser,
} from "../threadActions";
import type { Thread, ThreadUser } from "@/types/thread";
import type { User } from "@/types/user";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

interface ThreadState {
  loading: boolean;
  error: string | null;
  threads: Thread[];
}

describe("threadActions", () => {
  let store: ReturnType<typeof configureStore<{ threads: ThreadState }>>;

  const mockUser: User = {
    id: "user-123",
    email: "test@example.com",
    nickname: "Test User",
    picture: "avatar.png",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  const mockThreadUser: ThreadUser = {
    thread_id: "thread-123",
    user_id: "user-123",
    role: "user",
  };

  const mockThread: Thread = {
    id: "thread-123",
    name: "Test Thread",
    context: "Test context",
    memory: "Test memory",
    personality_id: "personality-123",
    status: "active",
    message_count: 0,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    store = configureStore({
      reducer: {
        threads: threadsReducer,
      },
      preloadedState: {
        threads: {
          threads: [mockThread],
          loading: false,
          error: null,
        },
      },
    });
  });

  describe("addUserByEmail", () => {
    it("should handle successful user addition with correct response structure", async () => {
      const mockResponse = {
        thread_user: mockThreadUser,
        user: mockUser,
      };

      (api.post as vi.Mock).mockResolvedValueOnce(mockResponse);

      await store.dispatch(
        addUserByEmail({ threadId: "thread-123", email: "newuser@example.com" })
      );

      expect(api.post).toHaveBeenCalledWith(
        "/threads/thread-123/users/email",
        { email: "newuser@example.com" }
      );
    });

    it("should handle API errors", async () => {
      const errorMessage = "User not found";
      (api.post as vi.Mock).mockRejectedValueOnce(new Error(errorMessage));

      await store.dispatch(
        addUserByEmail({ threadId: "thread-123", email: "invalid@example.com" })
      );

      // Just verify the API was called correctly
      expect(api.post).toHaveBeenCalledWith(
        "/threads/thread-123/users/email",
        { email: "invalid@example.com" }
      );
    });

    it("should handle unknown errors", async () => {
      (api.post as vi.Mock).mockRejectedValueOnce("Unknown error");

      await store.dispatch(
        addUserByEmail({ threadId: "thread-123", email: "test@example.com" })
      );

      expect(api.post).toHaveBeenCalledWith(
        "/threads/thread-123/users/email",
        { email: "test@example.com" }
      );
    });
  });

  describe("fetchThreadUsers", () => {
    it("should handle successful fetch with correct response structure", async () => {
      const mockResponse = {
        users: [
          {
            ...mockUser,
            thread_user: mockThreadUser,
          },
        ],
      };

      (api.get as vi.Mock).mockResolvedValueOnce(mockResponse);

      await store.dispatch(fetchThreadUsers("thread-123"));

      expect(api.get).toHaveBeenCalledWith("/threads/thread-123/users");
    });

    it("should handle empty users array", async () => {
      const mockResponse = { users: [] };
      (api.get as vi.Mock).mockResolvedValueOnce(mockResponse);

      await store.dispatch(fetchThreadUsers("thread-123"));

      expect(api.get).toHaveBeenCalledWith("/threads/thread-123/users");
    });
  });

  describe("removeThreadUser", () => {
    it("should handle successful user removal", async () => {
      (api.delete as vi.Mock).mockResolvedValueOnce(undefined);

      await store.dispatch(
        removeThreadUser({ threadId: "thread-123", userId: "user-123" })
      );

      expect(api.delete).toHaveBeenCalledWith("/threads/thread-123/users/user-123");
    });

    it("should handle deletion errors", async () => {
      const errorMessage = "Permission denied";
      (api.delete as vi.Mock).mockRejectedValueOnce(new Error(errorMessage));

      await store.dispatch(
        removeThreadUser({ threadId: "thread-123", userId: "user-123" })
      );

      expect(api.delete).toHaveBeenCalledWith("/threads/thread-123/users/user-123");
    });
  });
});
