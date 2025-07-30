import { configureStore } from "@reduxjs/toolkit";
import { vi } from "vitest";
import { joinPersonalityRoom, leavePersonalityRoom } from "../roomActions";

// Mock socket slice
vi.mock("../../slices/socketSlice", () => ({
  getConnectionStatus: vi.fn(() => true),
}));

// Mock room slice
vi.mock("../../slices/roomSlice", () => ({
  leaveRoom: vi.fn(),
  selectIsRoomSubscribed: vi.fn(() => false),
}));

// Mock WebSocketManager singleton
const mockHandlers: Record<string, any> = {};
vi.mock("../../WebSocketManager", () => ({
  socketManager: {
    sendMessage: vi.fn(),
    on: vi.fn((event, handler) => {
      mockHandlers[event] = handler;
      return { remove: vi.fn() };
    }),
    off: vi.fn(),
  },
}));

// Create a mock store
const createMockStore = () =>
  configureStore({
    reducer: {
      socket: (state = { connected: true }) => state,
      room: (state = { subscribedRooms: {} }) => state,
    },
  });

describe("roomActions", () => {
  let store: ReturnType<typeof createMockStore>;
  let mockSendMessage: any;

  beforeEach(async () => {
    store = createMockStore();
    vi.clearAllMocks();

    // Clear mock handlers
    Object.keys(mockHandlers).forEach(key => delete mockHandlers[key]);

    // Get the mocked socket manager
    const { socketManager } = await import("../../WebSocketManager");
    mockSendMessage = socketManager.sendMessage;
  });

  describe("joinPersonalityRoom", () => {
    it("should dispatch JoinPersonalityRoom WebSocket message successfully", async () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";

      // Start the join action
      const promise = store.dispatch(
        joinPersonalityRoom({ personalityId, roomId })
      );

      // Simulate the room_joined event
      await Promise.resolve(); // Let the action start

      if (mockHandlers.room_joined) {
        mockHandlers.room_joined({
          type: "room_joined",
          room_type: "personality_room",
          room_id: roomId,
          member_count: 1
        });
      }

      const result = await promise;

      expect(result.type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(result.payload).toEqual({ personalityId, roomId });
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: "JoinPersonalityRoom",
        personality_id: personalityId,
        room_id: roomId,
      });
    });

    it("should reject when socket is not connected", async () => {
      // Mock connection status as false
      const { getConnectionStatus } = await import("../../slices/socketSlice");
      vi.mocked(getConnectionStatus).mockReturnValueOnce(false);

      const personalityId = "test-personality-id";
      const roomId = "test-room-id";

      const result = await store.dispatch(
        joinPersonalityRoom({ personalityId, roomId })
      );

      expect(result.type).toBe("room/joinPersonalityRoom/rejected");
      expect(result.payload).toBe("Socket not connected");
      expect(mockSendMessage).not.toHaveBeenCalled();
    });
  });

  describe("leavePersonalityRoom", () => {
    it("should dispatch LeavePersonalityRoom WebSocket message successfully", async () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId, roomId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/fulfilled");
      expect(result.payload).toEqual({ personalityId, roomId });
      expect(mockSendMessage).toHaveBeenCalledWith({
        type: "LeavePersonalityRoom",
        personality_id: personalityId,
        room_id: roomId,
      });
    });

    it("should reject when socket is not connected", async () => {
      // Mock connection status as false for this test
      const { getConnectionStatus } = await import("../../slices/socketSlice");
      vi.mocked(getConnectionStatus).mockReturnValueOnce(false);

      const personalityId = "test-personality-id";
      const roomId = "test-room-id";

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId, roomId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/rejected");
      expect(result.payload).toBe("Socket not connected");
      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it("should handle WebSocket errors", async () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";
      const error = new Error("WebSocket error");
      mockSendMessage.mockImplementationOnce(() => {
        throw error;
      });

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId, roomId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/rejected");
      expect(result.payload).toBe("WebSocket error");
    });

    it("should handle unknown errors", async () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";
      mockSendMessage.mockImplementationOnce(() => {
        throw "Unknown error";
      });

      const result = await store.dispatch(
        leavePersonalityRoom({ personalityId, roomId })
      );

      expect(result.type).toBe("room/leavePersonalityRoom/rejected");
      expect(result.payload).toBe("Failed to leave personality room");
    });
  });

  describe("action creators", () => {
    it("should create correct action for joinPersonalityRoom pending", () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";
      const action = joinPersonalityRoom.pending("requestId", { personalityId, roomId });

      expect(action.type).toBe("room/joinPersonalityRoom/pending");
      expect(action.meta.arg).toEqual({ personalityId, roomId });
    });

    it("should create correct action for joinPersonalityRoom fulfilled", () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";
      const payload = { personalityId, roomId };
      const action = joinPersonalityRoom.fulfilled(
        payload,
        "requestId",
        { personalityId, roomId }
      );

      expect(action.type).toBe("room/joinPersonalityRoom/fulfilled");
      expect(action.payload).toEqual(payload);
    });

    it("should create correct action for leavePersonalityRoom pending", () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";
      const action = leavePersonalityRoom.pending("requestId", { personalityId, roomId });

      expect(action.type).toBe("room/leavePersonalityRoom/pending");
      expect(action.meta.arg).toEqual({ personalityId, roomId });
    });

    it("should create correct action for leavePersonalityRoom fulfilled", () => {
      const personalityId = "test-personality-id";
      const roomId = "test-room-id";
      const payload = { personalityId, roomId };
      const action = leavePersonalityRoom.fulfilled(
        payload,
        "requestId",
        { personalityId, roomId }
      );

      expect(action.type).toBe("room/leavePersonalityRoom/fulfilled");
      expect(action.payload).toEqual(payload);
    });
  });
});
