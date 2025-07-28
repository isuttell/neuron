import { useEffect, useCallback } from "react";
import { UseRoomReturn } from "./useRoom";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  joinRoomStart,
  joinRoomFailure,
  selectIsRoomSubscribed,
  selectRoomJoinPending,
  selectRoomError,
  selectRoomMemberCount,
} from "../slices/roomSlice";
import { getConnectionStatus } from "../slices/socketSlice";
import { joinPersonalityRoom, leavePersonalityRoom } from "../actions/roomActions";


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
  // Import needed hooks and actions
  const dispatch = useAppDispatch();
  const isConnected = useAppSelector(getConnectionStatus);

  // Room state selectors - use room-specific subscriptions
  const isSubscribed = useAppSelector((state) =>
    roomId ? selectIsRoomSubscribed(state, "personality_room", roomId) : false
  );
  const isJoining = useAppSelector((state) =>
    roomId ? selectRoomJoinPending(state, "personality_room", roomId) : false
  );
  const error = useAppSelector((state) =>
    roomId ? selectRoomError(state, "personality_room", roomId) : undefined
  );
  const memberCount = useAppSelector((state) =>
    roomId ? selectRoomMemberCount(state, "personality_room", roomId) : 0
  );

  // Manual join function for personality rooms
  const joinRoom = useCallback(async (): Promise<void> => {
    if (!personalityId || !roomId || !isConnected || isSubscribed) {
      return;
    }

    try {
      dispatch(joinRoomStart({ roomType: "personality_room", roomId }));

      const result = await dispatch(joinPersonalityRoom({ personalityId, roomId }));
      if (joinPersonalityRoom.rejected.match(result)) {
        throw new Error(result.payload as string);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to join room";
      dispatch(joinRoomFailure({ roomType: "personality_room", roomId, error: errorMessage }));
      throw err;
    }
  }, [personalityId, roomId, isConnected, isSubscribed, dispatch]);

  // Manual leave function
  const leaveRoomManual = (): void => {
    if (!personalityId || !roomId || !isSubscribed) {
      return;
    }

    try {
      dispatch(leavePersonalityRoom({ personalityId, roomId }));
    } catch (err) {
      console.error(`Failed to leave personality room:`, err);
    }
  };

  // Auto-join effect
  useEffect(() => {
    if (!personalityId || !roomId || !isConnected || isSubscribed || isJoining) {
      return;
    }

    joinRoom().catch((err) => {
      console.error(`Failed to auto-join personality room:`, err);
    });
  }, [personalityId, roomId, isConnected, isSubscribed, isJoining, joinRoom]);

  // Cleanup effect
  useEffect(() => {
    const currentPersonalityId = personalityId;
    const currentRoomId = roomId;

    return () => {
      if (currentPersonalityId && currentRoomId) {
        dispatch(leavePersonalityRoom({ personalityId: currentPersonalityId, roomId: currentRoomId }));
      }
    };
  }, []); // Only run on mount/unmount

  return {
    isSubscribed,
    isJoining,
    error,
    memberCount,
    joinRoom,
    leaveRoom: leaveRoomManual,
    personalityId,
    roomId,
  };
};
