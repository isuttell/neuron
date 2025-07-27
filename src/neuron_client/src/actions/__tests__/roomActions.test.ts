import { configureStore } from "@reduxjs/toolkit";
import { vi } from "vitest";
import { joinPersonalityRoom, leavePersonalityRoom } from "../roomActions";

// Mock socket slice
vi.mock("../../slices/socketSlice", () => ({
  getConnectionStatus: vi.fn(() => true),
}));

// Mock WebSocketManager singleton
vi.mock("../../WebSocketManager", () => ({
  socketManager: {
    sendMessage: vi.fn(),
  },
}));

// Create a mock store
const createMockStore = () =>
  configureStore({
    reducer: {
      socket: (state = { connected: true }) => state,
    },
  });

describe("roomActions", () => {
  let store: ReturnType<typeof createMockStore>;
  let mockSendMessage: any;

  beforeEach(async () => {
    store = createMockStore();
    vi.clearAllMocks();

    // Get the mocked socket manager
    const { socketManager } = await import("../../WebSocketManager");
    mockSendMessage = socketManager.sendMessage;
  });

  describe("joinPersonalityRoom", () => {
    it("should dispatch JoinPersonalityRoom WebSocket message successfully", async () => {
      const personalityId = "test-personality-id";

      const result = await store.dispatch(
        joinPersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(result.payload).toEqual({ personalityId });
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: "JoinPersonalityRoom",
        personality_id: personalityId,
      });
    });

    it("should reject when socket is not connected", async () => {
      // Mock connection status as false
      const { getConnectionStatus } = await import("../../slices/socketSlice");
      vi.mocked(getConnectionStatus).mockReturnValueOnce(false);

      const personalityId = "test-personality-id";

      const result = await store.dispatch(
        joinPersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/joinPersonalityRoom/rejected");
      expect(result.payload).toBe("Socket not connected");
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it("should handle WebSocket errors", async () => {
      const personalityId = "test-personality-id";
      const error = new Error("WebSocket error");
      mockSendMessage.mockImplementationOnce(() => {
        throw error;
      });

      const result = await store.dispatch(
        joinPersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/joinPersonalityRoom/rejected");
      expect(result.payload).toBe("WebSocket error");
    });

    it("should handle unknown errors", async () => {
      const personalityId = "test-personality-id";
      mockSendMessage.mockImplementationOnce(() => {
        throw "Unknown error";
      });

      const result = await store.dispatch(
        joinPersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/joinPersonalityRoom/rejected");
      expect(result.payload).toBe("Failed to join personality room");
    });
  });

  describe("leavePersonalityRoom", () => {
    it("should dispatch LeavePersonalityRoom WebSocket message successfully", async () => {
      const personalityId = "test-personality-id";

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/fulfilled");
      expect(result.payload).toEqual({ personalityId });
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: "LeavePersonalityRoom",
        personality_id: personalityId,
      });
    });

    it("should reject when socket is not connected", async () => {
      // Mock connection status as false for this test
      const { getConnectionStatus } = await import("../../slices/socketSlice");
      vi.mocked(getConnectionStatus).mockReturnValueOnce(false);

      const personalityId = "test-personality-id";

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/rejected");
      expect(result.payload).toBe("Socket not connected");
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it("should handle WebSocket errors", async () => {
      const personalityId = "test-personality-id";
      const error = new Error("WebSocket error");
      mockSendMessage.mockImplementationOnce(() => {
        throw error;
      });

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/rejected");
      expect(result.payload).toBe("WebSocket error");
    });

    it("should handle unknown errors", async () => {
      const personalityId = "test-personality-id";
      mockSendMessage.mockImplementationOnce(() => {
        throw "Unknown error";
      });

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/rejected");
      expect(result.payload).toBe("Failed to leave personality room");
    });
  });

  describe("action creators", () => {
    it("should create correct action for joinPersonalityRoom pending", () => {
      const personalityId = "test-personality-id";
      const action = joinPersonalityRoom.pending("requestId", { personalityId });

      expect(action.type).toBe("room/joinPersonalityRoom/pending");
      expect(action.meta.arg).toEqual({ personalityId });
    });

    it("should create correct action for joinPersonalityRoom fulfilled", () => {
      const personalityId = "test-personality-id";
      const payload = { personalityId };
      const action = joinPersonalityRoom.fulfilled(
        payload,
        "requestId",
        { personalityId }
      );

      expect(action.type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(action.payload).toEqual(payload);
    });

    it("should create correct action for leavePersonalityRoom pending", () => {
      const personalityId = "test-personality-id";
      const action = leavePersonalityRoom.pending("requestId", { personalityId });

      expect(action.type).toBe("room/leavePersonalityRoom/pending");
      expect(action.meta.arg).toEqual({ personalityId });
    });

    it("should create correct action for leavePersonalityRoom fulfilled", () => {
      const personalityId = "test-personality-id";
      const payload = { personalityId };
      const action = leavePersonalityRoom.fulfilled(
        payload,
        "requestId",
        { personalityId }
      );

      expect(action.type).toBe("room/leavePersonalityRoom/fulfilled");
      expect(action.payload).toEqual(payload);
    });
  });

  describe("thunk behavior", () => {
    it("should handle multiple concurrent join requests", async () => {
      const personalityId1 = "personality-1";
      const personalityId2 = "personality-2";

      const promises = [
        store.dispatch(joinPersonalityRoom({ personalityId: personalityId1 })),
        store.dispatch(joinPersonalityRoom({ personalityId: personalityId2 })),
      ];

      const results = await Promise.all(promises);

      expect(results[0].type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(results[1].type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(results[0].payload).toEqual({ personalityId: personalityId1 });
      expect(results[1].payload).toEqual({ personalityId: personalityId2 });
      expect(mockSendMessage).toHaveBeenCalledTimes(2);
    });

    it("should handle join followed by leave", async () => {
      const personalityId = "test-personality-id";

      const joinResult = await store.dispatch(
        joinPersonalityRoom({ personalityId })
      );
      const leaveResult = await store.dispatch(
        leavePersonalityRoom({ personalityId })
      );

      expect(joinResult.type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(leaveResult.type).toBe("room/leavePersonalityRoom/fulfilled");
      expect(mockSendMessage).toHaveBeenCalledTimes(2);
      expect(mockSendMessage).toHaveBeenNthCalledWith(1, {
        type: "JoinPersonalityRoom",
        personality_id: personalityId,
      });
      expect(mockSendMessage).toHaveBeenNthCalledWith(2, {
        type: "LeavePersonalityRoom",
        personality_id: personalityId,
      });
    });
  });
});
