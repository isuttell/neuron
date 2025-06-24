import type { User } from "@auth0/auth0-react";
import type { Personality, PersonalityUser } from "../types/personality";
import { isAdmin } from "../lib/auth";

/**
 * Check if the current user is an admin of the personality (has admin role in personality_users)
 */
export function isPersonalityAdmin(user: User | undefined, personality: Personality | undefined): boolean {
  if (!user?.sub || !personality?.personality_users) {
    return false;
  }

  const personalityUser = personality.personality_users.find((pu: PersonalityUser) => pu.user_id === user.sub);
  return personalityUser?.role === "admin";
}

/**
 * Check if the current user can manage the personality (edit, delete, manage users)
 */
export function canManagePersonality(user: User | undefined, personality: Personality | undefined): boolean {
  // System admins can always manage personalities
  if (isAdmin(user)) {
    return true;
  }
  // Personality admins can manage
  return isPersonalityAdmin(user, personality);
}

/**
 * Check if the current user can use the personality
 */
export function canUsePersonality(user: User | undefined, personality: Personality | undefined): boolean {
  if (!user?.sub || !personality) {
    return false;
  }

  // System admins can use any personality
  if (isAdmin(user)) {
    return true;
  }

  // Check if user has any role for this personality
  if (personality.personality_users) {
    return personality.personality_users.some((pu: PersonalityUser) => pu.user_id === user.sub);
  }

  return false;
}

/**
 * Check if the current user can manage personality users (add/remove users, change roles)
 */
export function canManagePersonalityUsers(user: User | undefined, personality: Personality | undefined): boolean {
  // System admins can always manage users
  if (isAdmin(user)) {
    return true;
  }
  // Personality admins can manage users
  return isPersonalityAdmin(user, personality);
}

/**
 * Check if the current user can delete the personality
 */
export function canDeletePersonality(user: User | undefined, personality: Personality | undefined): boolean {
  // System admins can always delete
  if (isAdmin(user)) {
    return true;
  }
  // Personality admins can delete
  return isPersonalityAdmin(user, personality);
}

/**
 * Check if the current user has any access to the personality
 */
export function hasPersonalityAccess(user: User | undefined, personality: Personality | undefined): boolean {
  if (!user?.sub || !personality) {
    return false;
  }

  // System admins have access to all personalities
  if (isAdmin(user)) {
    return true;
  }

  // Check if user is in personality_users
  if (personality.personality_users) {
    return personality.personality_users.some((pu: PersonalityUser) => pu.user_id === user.sub);
  }

  return false;
}

/**
 * Check if the current user has any personality actions available
 */
export function hasAnyPersonalityActions(user: User | undefined, personality: Personality | undefined): boolean {
  // System admins can always act
  if (isAdmin(user)) {
    return true;
  }

  // Check if user has any personality-level permissions
  return (
    canManagePersonality(user, personality) ||
    canManagePersonalityUsers(user, personality) ||
    canDeletePersonality(user, personality)
  );
}

/**
 * Get the current user's role in the personality
 */
export function getPersonalityUserRole(user: User | undefined, personality: Personality | undefined): string | null {
  if (!user?.sub || !personality) {
    return null;
  }

  // Check explicit role in personality_users
  if (personality.personality_users) {
    const personalityUser = personality.personality_users.find((pu: PersonalityUser) => pu.user_id === user.sub);
    return personalityUser?.role || null;
  }

  return null;
}
