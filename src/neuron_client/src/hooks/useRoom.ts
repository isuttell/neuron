import { useEffect, useRef, useCallback } from "react";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  joinRoomStart,
  joinRoomFailure,
  leaveRoom,
  selectIsRoomSubscribed,
  selectRoomJoinPending,
  selectRoomError,
  selectRoomMemberCount,
} from "../slices/roomSlice";
import { getConnectionStatus } from "../slices/socketSlice";

export interface UseRoomOptions {
  /** Whether to automatically join the room when dependencies are ready */
  autoJoin?: boolean;
  /** Whether to automatically leave the room on unmount */
  autoLeave?: boolean;
}

export interface UseRoomReturn {
  /** Whether the user is subscribed to this room */
  isSubscribed: boolean;
  /** Whether a join operation is currently pending */
  isJoining: boolean;
  /** Any error that occurred during room operations */
  error: string | undefined;
  /** Number of members in the room (0 if not subscribed) */
  memberCount: number;
  /** Function to manually join the room */
  joinRoom: () => Promise<void>;
  /** Function to manually leave the room */
  leaveRoom: () => void;
}

/**
 * Base hook for managing room subscriptions
 *
 * @param roomType - Type of room (e.g., 'personality', 'thread')
 * @param roomId - Unique identifier for the room
 * @param options - Configuration options for room behavior
 * @returns Room subscription state and control functions
 */
export const useRoom = (
  roomType: string,
  roomId: string | undefined,
  options: UseRoomOptions = {}
): UseRoomReturn => {
  const { autoJoin = true, autoLeave = true } = options;

  const dispatch = useAppDispatch();
  const isConnected = useAppSelector(getConnectionStatus);

  // Room state selectors
  const isSubscribed = useAppSelector((state) =>
    roomId ? selectIsRoomSubscribed(state, roomType, roomId) : false
  );
  const isJoining = useAppSelector((state) =>
    roomId ? selectRoomJoinPending(state, roomType, roomId) : false
  );
  const error = useAppSelector((state) =>
    roomId ? selectRoomError(state, roomType, roomId) : undefined
  );
  const memberCount = useAppSelector((state) =>
    roomId ? selectRoomMemberCount(state, roomType, roomId) : 0
  );

  // Use ref to track current subscription status for cleanup
  const isSubscribedRef = useRef(isSubscribed);
  isSubscribedRef.current = isSubscribed;

  // Manual join function
  const joinRoomManual = useCallback(async (): Promise<void> => {
    if (!roomId || !isConnected || isSubscribed) {
      return;
    }

    try {
      // Dispatch start action to update pending state
      dispatch(joinRoomStart({ roomType, roomId }));

      // Use appropriate join action based on room type
      if (roomType === "personality_room") {
        // For personality rooms, we need both personalityId and roomId
        // The roomId parameter contains the actual room ID
        // We'll need to get the personalityId from somewhere else
        throw new Error("personality room type requires usePersonalityRoom hook");
      } else {
        throw new Error(`Unsupported room type: ${roomType}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to join room";
      dispatch(joinRoomFailure({ roomType, roomId, error: errorMessage }));
      throw err;
    }
  }, [roomId, isConnected, isSubscribed, dispatch, roomType]);

  // Manual leave function
  const leaveRoomManual = (): void => {
    if (!roomId || !isSubscribed) {
      return;
    }

    try {
      // Use appropriate leave action based on room type
      if (roomType === "personality_room") {
        // For personality rooms, we need both personalityId and roomId
        throw new Error("personality room type requires usePersonalityRoom hook");
      } else {
        throw new Error(`Unsupported room type: ${roomType}`);
      }
    } catch (err) {
      console.error(`Failed to leave ${roomType} room:`, err);
      // Update local state even if the action fails
      dispatch(leaveRoom({ roomType, roomId }));
    }
  };

  // Auto-join effect
  useEffect(() => {
    if (!autoJoin || !roomId || !isConnected || isSubscribed || isJoining) {
      return;
    }
    // Join the room when conditions are met
    joinRoomManual().catch((err) => {
      console.error(`Failed to auto-join ${roomType} room:`, err);
    });
  }, [roomType, roomId, isConnected, isSubscribed, isJoining, autoJoin, joinRoomManual]);

  // Dedicated cleanup effect - runs only on mount/unmount
  useEffect(() => {
    // Store initial values for cleanup
    const initialRoomType = roomType;
    const initialRoomId = roomId;
    const initialAutoLeave = autoLeave;

    return () => {
      // Always attempt cleanup on unmount, regardless of current state
      if (initialAutoLeave && initialRoomId) {
        console.log("Cleanup: leaving room", initialRoomType, initialRoomId);

        // Direct dispatch without going through functions to avoid stale references
        if (initialRoomType === "personality_room") {
          // Note: personality rooms require both IDs, so this won't work
          // They should use usePersonalityRoom hook instead
          console.warn("personality room type requires usePersonalityRoom hook for cleanup");
        }

        // Update local state
        dispatch(leaveRoom({ roomType: initialRoomType, roomId: initialRoomId }));
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array - only runs on mount/unmount

  return {
    isSubscribed,
    isJoining,
    error,
    memberCount,
    joinRoom: joinRoomManual,
    leaveRoom: leaveRoomManual,
  };
};
