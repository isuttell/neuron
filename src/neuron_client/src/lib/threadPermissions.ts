import type { User } from "@auth0/auth0-react";
import type { Thread, ThreadUser } from "../types/thread";
import { isAdmin } from "../lib/auth";

/**
 * Check if the current user is the owner of the thread
 */
export function isThreadOwner(user: User | undefined, thread: Thread | undefined): boolean {
  if (!user?.sub || !thread?.user_id) {
    return false;
  }
  return user.sub === thread.user_id;
}

/**
 * Check if the current user is an admin of the thread (has admin role in thread_users)
 */
export function isThreadAdmin(user: User | undefined, thread: Thread | undefined): boolean {
  if (!user?.sub || !thread?.thread_users) {
    return false;
  }

  const threadUser = thread.thread_users.find((tu: ThreadUser) => tu.user_id === user.sub);
  return threadUser?.role === "admin";
}

/**
 * Check if the current user has admin-level permissions (owner or admin)
 */
export function hasThreadAdminPermissions(user: User | undefined, thread: Thread | undefined): boolean {
  return isThreadOwner(user, thread) || isThreadAdmin(user, thread);
}

/**
 * Check if the current user can manage the thread (edit personality, settings)
 */
export function canManageThread(user: User | undefined, thread: Thread | undefined): boolean {
  // System admins can always manage
  if (isAdmin(user)) {
    return true;
  }
  // Thread owners/admins can manage
  return hasThreadAdminPermissions(user, thread);
}

/**
 * Check if the current user can manage thread users (add/remove users, change roles)
 */
export function canManageUsers(user: User | undefined, thread: Thread | undefined): boolean {
  // System admins can always manage users
  if (isAdmin(user)) {
    return true;
  }
  // Thread owners/admins can manage users
  return hasThreadAdminPermissions(user, thread);
}

/**
 * Check if the current user can delete the thread
 */
export function canDeleteThread(user: User | undefined, thread: Thread | undefined): boolean {
  // System admins can always delete
  if (isAdmin(user)) {
    return true;
  }
  // Only thread owners can delete (not thread admins)
  return isThreadOwner(user, thread);
}

/**
 * Check if the current user has any access to the thread
 */
export function hasThreadAccess(user: User | undefined, thread: Thread | undefined): boolean {
  if (!user?.sub || !thread) {
    return false;
  }

  // Thread owner always has access
  if (isThreadOwner(user, thread)) {
    return true;
  }

  // Check if user is in thread_users
  if (thread.thread_users) {
    return thread.thread_users.some((tu: ThreadUser) => tu.user_id === user.sub);
  }

  return false;
}

/**
 * Check if the current user can view system messages (only system admins)
 */
export function canViewSystemMessages(user: User | undefined): boolean {
  return isAdmin(user);
}

/**
 * Check if the current user has any thread actions available
 * Note: This excludes personality management actions which are handled separately
 */
export function hasAnyThreadActions(user: User | undefined, thread: Thread | undefined): boolean {
  // System admins can always act on threads
  if (isAdmin(user)) {
    return true;
  }

  // Check if user has any thread-level permissions (excluding personality actions)
  return (
    canManageThread(user, thread) ||
    canManageUsers(user, thread) ||
    canDeleteThread(user, thread) ||
    canViewSystemMessages(user)
  );
}

/**
 * Get the current user's role in the thread
 */
export function getThreadUserRole(user: User | undefined, thread: Thread | undefined): string | null {
  if (!user?.sub || !thread) {
    return null;
  }

  // Thread owner has implicit admin role
  if (isThreadOwner(user, thread)) {
    return "owner";
  }

  // Check explicit role in thread_users
  if (thread.thread_users) {
    const threadUser = thread.thread_users.find((tu: ThreadUser) => tu.user_id === user.sub);
    return threadUser?.role || null;
  }

  return null;
}
