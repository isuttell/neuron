import { useAuth0 } from "@auth0/auth0-react";
import { useMemo } from "react";
import {
  getUserPermissions,
  getUserRoles,
  hasPermission,
  hasRole,
  isAdmin,
  canAccessPrompts,
  canAccessProviders,
  canAccessMicroApps,
  PERMISSIONS,
  ROLES
} from "@/lib/auth";

/**
 * Custom hook for accessing user permissions and roles
 */
export function usePermissions() {
  const { user } = useAuth0();

  return useMemo(() => ({
    // Raw data
    permissions: getUserPermissions(user),
    roles: getUserRoles(user),

    // Utility functions bound to current user
    hasPermission: (permission: string) => hasPermission(user, permission),
    hasRole: (role: string) => hasRole(user, role),

    // Convenience flags
    isAdmin: isAdmin(user),
    canAccessPrompts: canAccessPrompts(user),
    canAccessProviders: canAccessProviders(user),
    canAccessMicroApps: canAccessMicroApps(user),

    // Constants for easy access
    PERMISSIONS,
    ROLES,
  }), [user]);
}
