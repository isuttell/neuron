import { useMemo } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useAppSelector } from "../hooks";
import { getPersonalityRoom, getRoomUsers } from "../slices/personalityRoomSlice";

/**
 * Hook to get personality room-level permissions for the current user
 */
export function usePersonalityRoomPermissions(_personalityId: string | undefined, roomId: string | undefined) {
  const { user } = useAuth0();
  const room = useAppSelector((state) =>
    roomId ? getPersonalityRoom(state, roomId) : undefined
  );
  const roomUsers = useAppSelector((state) =>
    roomId ? getRoomUsers(state, roomId) : []
  );

  return useMemo(() => {
    if (!user || !room) {
      return {
        room: undefined,
        isRoomAdmin: false,
        canManageUsers: false,
        canDelete: false,
        hasAnyActions: false,
      };
    }

    // Check if user is room admin
    const roomUser = roomUsers.find(ru => ru.user_id === user.sub);
    const isRoomAdmin = room.created_by === user.sub || roomUser?.role === "admin";

    // Only room admins can do anything
    const canManageUsers = isRoomAdmin;
    const canDelete = isRoomAdmin;
    const hasAnyActions = isRoomAdmin;

    return {
      room,
      isRoomAdmin,
      canManageUsers,
      canDelete,
      hasAnyActions,
    };
  }, [user, room, roomUsers]);
}
