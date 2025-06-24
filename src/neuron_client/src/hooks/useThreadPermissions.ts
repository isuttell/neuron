import { useMemo } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useAppSelector } from "../hooks";
import { selectThread } from "../slices/threadsSlice";
import {
  isThreadOwner,
  isThreadAdmin,
  hasThreadAdminPermissions,
  canManageThread,
  canManageUsers,
  canDeleteThread,
  hasThreadAccess,
  getThreadUserRole,
  canViewSystemMessages,
  hasAnyThreadActions,
} from "../lib/threadPermissions";

/**
 * Hook to get thread-level permissions for the current user
 */
export function useThreadPermissions(threadId: string | undefined) {
  const { user } = useAuth0();
  const thread = useAppSelector((state) =>
    threadId ? selectThread(state, threadId) : undefined
  );

  return useMemo(() => {
    const userRole = getThreadUserRole(user, thread);
    const hasAccess = hasThreadAccess(user, thread);
    const isOwner = isThreadOwner(user, thread);
    const isAdmin = isThreadAdmin(user, thread);
    const hasAdminPermissions = hasThreadAdminPermissions(user, thread);

    // Calculate permissions
    const canManage = canManageThread(user, thread);
    const canManageUsersPermission = canManageUsers(user, thread);
    const canDelete = canDeleteThread(user, thread);
    const canViewMessages = canViewSystemMessages(user);
    const hasAnyActions = hasAnyThreadActions(user, thread);

    return {
      // Thread data
      thread: thread || undefined,
      userRole,

      // Permission flags
      isOwner,
      isAdmin,
      hasAdminPermissions,
      hasAccess,

      // Action permissions
      canManage,
      canManageUsers: canManageUsersPermission,
      canDelete,
      canViewSystemMessages: canViewMessages,
      hasAnyActions,

      // Component visibility
      shouldShowComponent: hasAnyActions,
    };
  }, [user, thread]);
}
