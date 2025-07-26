import { useRoom, UseRoomReturn } from "./useRoom";


export interface UsePersonalityRoomReturn extends UseRoomReturn {
  /** The personality ID for this room */
  personalityId: string | undefined;
}

/**
 * Specialized hook for managing personality room subscriptions
 *
 * Extends the base useRoom hook with personality-specific functionality:
 * - Simplified API: only requires personalityId
 * - Auto-fetches messages when joining room (optional)
 * - Type-safe personality ID handling
 * - Personality-specific error handling
 *
 * @param personalityId - The ID of the personality to join room for
 * @param options - Configuration options extending base room options
 * @returns Personality room subscription state and control functions
 */
export const usePersonalityRoom = (
  personalityId: string | undefined,
): UsePersonalityRoomReturn => {

  // Use base room hook with personality room type
  const roomState = useRoom("personality", personalityId);

  return {
    ...roomState,
    personalityId,
  };
};
