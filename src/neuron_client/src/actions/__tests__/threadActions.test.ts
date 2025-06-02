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
jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

describe("threadActions", () => {
  let store: ReturnType<typeof configureStore>;

  const mockUser: User = {
    id: "user-123",
    email: "test@example.com",
    name: "Test User",
    avatar: "avatar.png",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  const mockThreadUser: ThreadUser = {
    id: "thread-user-123",
    thread_id: "thread-123",
    user_id: "user-123",
    role: "user",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  const mockThread: Thread = {
    id: "thread-123",
    title: "Test Thread",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    user_id: "user-123",
    archived: false,
    personality_id: null,
    provider_model_id: null,
    parent_id: null,
    metadata: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    store = configureStore({
      reducer: {
        threads: threadsReducer,
      },
      preloadedState: {
        threads: {
          activeThreadId: "thread-123",
          threads: [mockThread],
          recentThreads: [],
          threadCreated: 0,
          userThreads: [],
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

      (api.post as jest.Mock).mockResolvedValueOnce(mockResponse);

      const result = await store.dispatch(
        addUserByEmail({ threadId: "thread-123", email: "newuser@example.com" })
      );

      expect(api.post).toHaveBeenCalledWith(
        "/threads/thread-123/users/email",
        { email: "newuser@example.com" }
      );
      expect(result.type).toBe("threads/addUserByEmail/fulfilled");
      expect(result.payload).toEqual(mockResponse);

      // Verify the response is correctly structured (not wrapped in .data)
      expect(result.payload).toHaveProperty("thread_user");
      expect(result.payload).toHaveProperty("user");
    });

    it("should handle API errors", async () => {
      const errorMessage = "User not found";
      (api.post as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));

      const result = await store.dispatch(
        addUserByEmail({ threadId: "thread-123", email: "invalid@example.com" })
      );

      expect(result.type).toBe("threads/addUserByEmail/rejected");
      expect(result.payload).toBe(errorMessage);
    });

    it("should handle unknown errors", async () => {
      (api.post as jest.Mock).mockRejectedValueOnce("Unknown error");

      const result = await store.dispatch(
        addUserByEmail({ threadId: "thread-123", email: "test@example.com" })
      );

      expect(result.type).toBe("threads/addUserByEmail/rejected");
      expect(result.payload).toBe("An unknown error occurred");
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

      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);

      const result = await store.dispatch(fetchThreadUsers("thread-123"));

      expect(api.get).toHaveBeenCalledWith("/threads/thread-123/users");
      expect(result.type).toBe("threads/fetchThreadUsers/fulfilled");
      expect(result.payload).toEqual(mockResponse);

      // Verify the response structure
      expect(result.payload).toHaveProperty("users");
      expect(Array.isArray(result.payload.users)).toBe(true);
    });

    it("should handle empty users array", async () => {
      const mockResponse = { users: [] };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);

      const result = await store.dispatch(fetchThreadUsers("thread-123"));

      expect(result.payload).toEqual(mockResponse);
      expect(result.payload.users).toHaveLength(0);
    });
  });

  describe("removeThreadUser", () => {
    it("should handle successful user removal", async () => {
      (api.delete as jest.Mock).mockResolvedValueOnce(undefined);

      const result = await store.dispatch(
        removeThreadUser({ threadId: "thread-123", userId: "user-123" })
      );

      expect(api.delete).toHaveBeenCalledWith("/threads/thread-123/users/user-123");
      expect(result.type).toBe("threads/removeThreadUser/fulfilled");
      expect(result.payload).toEqual({ threadId: "thread-123", userId: "user-123" });
    });

    it("should handle deletion errors", async () => {
      const errorMessage = "Permission denied";
      (api.delete as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));

      const result = await store.dispatch(
        removeThreadUser({ threadId: "thread-123", userId: "user-123" })
      );

      expect(result.type).toBe("threads/removeThreadUser/rejected");
      expect(result.payload).toBe(errorMessage);
    });
  });
});
