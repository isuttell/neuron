import { useRoom, UseRoomReturn } from "./useRoom";


export interface UsePersonalityRoomReturn extends UseRoomReturn {
  /** The personality ID for this room */
  personalityId: string | undefined;
  /** The room ID for this room */
  roomId: string | undefined;
}

/**
 * Specialized hook for managing personality room subscriptions
 *
 * Extends the base useRoom hook with personality-specific functionality:
 * - Simplified API: requires personalityId and roomId
 * - Auto-fetches messages when joining room (optional)
 * - Type-safe personality ID and room ID handling
 * - Personality-specific error handling
 *
 * @param personalityId - The ID of the personality to join room for
 * @param roomId - The ID of the specific room to join
 * @param options - Configuration options extending base room options
 * @returns Personality room subscription state and control functions
 */
export const usePersonalityRoom = (
  personalityId: string | undefined,
  roomId: string | undefined,
): UsePersonalityRoomReturn => {

  // Use base room hook with personality room type
  // For now, we still join the personality-wide room for WebSocket events
  // TODO: Update backend to support room-specific WebSocket subscriptions
  const roomState = useRoom("personality", personalityId);

  return {
    ...roomState,
    personalityId,
    roomId,
  };
};
