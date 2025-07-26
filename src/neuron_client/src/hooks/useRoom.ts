import { useEffect, useRef } from "react";
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
import { joinPersonalityRoom, leavePersonalityRoom } from "../actions/roomActions";

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
  const joinRoomManual = async (): Promise<void> => {
    if (!roomId || !isConnected || isSubscribed) {
      return;
    }

    try {
      // Dispatch start action to update pending state
      dispatch(joinRoomStart({ roomType, roomId }));

      // Use appropriate join action based on room type
      if (roomType === "personality") {
        const result = await dispatch(joinPersonalityRoom({ personalityId: roomId }));
        if (joinPersonalityRoom.rejected.match(result)) {
          throw new Error(result.payload as string);
        }
      } else {
        throw new Error(`Unsupported room type: ${roomType}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to join room";
      dispatch(joinRoomFailure({ roomType, roomId, error: errorMessage }));
      throw err;
    }
  };

  // Manual leave function
  const leaveRoomManual = (): void => {
    if (!roomId || !isSubscribed) {
      return;
    }

    try {
      // Use appropriate leave action based on room type
      if (roomType === "personality") {
        dispatch(leavePersonalityRoom({ personalityId: roomId }));
      } else {
        throw new Error(`Unsupported room type: ${roomType}`);
      }

      // Update local state immediately
      dispatch(leaveRoom({ roomType, roomId }));
    } catch (err) {
      console.error(`Failed to leave ${roomType} room:`, err);
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
  }, [roomType, roomId, isConnected, isSubscribed, isJoining, autoJoin]);

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
        if (initialRoomType === "personality") {
          dispatch(leavePersonalityRoom({ personalityId: initialRoomId }));
        }

        // Update local state
        dispatch(leaveRoom({ roomType: initialRoomType, roomId: initialRoomId }));
      }
    };
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
