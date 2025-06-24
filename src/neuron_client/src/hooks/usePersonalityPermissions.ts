import { useMemo } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useAppSelector } from "../hooks";
import { getPersonality, getPersonalityUsers } from "../slices/personalitiesSlice";
import {
  isPersonalityAdmin,
  canManagePersonality,
  canUsePersonality,
  canManagePersonalityUsers,
  canDeletePersonality,
  hasPersonalityAccess,
  getPersonalityUserRole,
  hasAnyPersonalityActions,
} from "../lib/personalityPermissions";
import type { Personality } from "../types/personality";

/**
 * Hook to get personality-level permissions for the current user
 */
export function usePersonalityPermissions(personalityId: string | undefined) {
  const { user } = useAuth0();
  const personality = useAppSelector((state) =>
    personalityId ? getPersonality(state, personalityId) : undefined
  );
  const personalityUsers = useAppSelector((state) =>
    personalityId ? getPersonalityUsers(state, personalityId) : []
  );

  return useMemo(() => {
    // Convert UserWithRole[] from Redux to PersonalityUser[] format
    const convertedPersonalityUsers = personalityUsers.map(userWithRole => ({
      user_id: userWithRole.id,
      personality_id: personalityId || '',
      role: userWithRole.role
    }));

    // Merge personality_users from Redux store into personality object
    const personalityWithUsers: Personality | undefined = personality ? {
      ...personality,
      personality_users: convertedPersonalityUsers
    } : undefined;

    const userRole = getPersonalityUserRole(user, personalityWithUsers);
    const hasAccess = hasPersonalityAccess(user, personalityWithUsers);
    const isAdmin = isPersonalityAdmin(user, personalityWithUsers);

    // Calculate permissions
    const canManage = canManagePersonality(user, personalityWithUsers);
    const canManageUsersPermission = canManagePersonalityUsers(user, personalityWithUsers);
    const canDelete = canDeletePersonality(user, personalityWithUsers);
    const canUse = canUsePersonality(user, personalityWithUsers);
    const hasAnyActions = hasAnyPersonalityActions(user, personalityWithUsers);

    return {
      // Personality data
      personality: personalityWithUsers || undefined,
      userRole,

      // Permission flags
      isAdmin,
      hasAccess,

      // Action permissions
      canManage,
      canManageUsers: canManageUsersPermission,
      canDelete,
      canUse,
      hasAnyActions,

      // Component visibility
      shouldShowComponent: hasAnyActions,
    };
  }, [user, personality, personalityUsers, personalityId]);
}
