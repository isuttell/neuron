import { User } from "@auth0/auth0-react";

/**
 * Permission constants to avoid magic strings throughout the codebase
 */
export const PERMISSIONS = {
  ADMIN_PROMPTS: "admin-prompts",
  ADMIN_PROVIDERS: "admin-providers",
  ADMIN: "admin", // For backwards compatibility with roles
} as const;

/**
 * Role constants to avoid magic strings
 */
export const ROLES = {
  ADMIN: "admin",
} as const;

/**
 * Extract user permissions from Auth0 user object
 */
export function getUserPermissions(user: User | undefined): string[] {
  return (user?.["permissions"] as string[]) || [];
}

/**
 * Extract user roles from Auth0 user object
 */
export function getUserRoles(user: User | undefined): string[] {
  return (user?.["neuron/roles"] as string[]) || [];
}

/**
 * Check if user has a specific permission
 */
export function hasPermission(user: User | undefined, permission: string): boolean {
  const permissions = getUserPermissions(user);
  return permissions.includes(permission);
}

/**
 * Check if user has a specific role
 */
export function hasRole(user: User | undefined, role: string): boolean {
  const roles = getUserRoles(user);
  return roles.includes(role);
}

/**
 * Check if user has admin role (backwards compatibility)
 */
export function isAdmin(user: User | undefined): boolean {
  return hasRole(user, ROLES.ADMIN);
}

/**
 * Check if user can access prompts admin features
 */
export function canAccessPrompts(user: User | undefined): boolean {
  return hasPermission(user, PERMISSIONS.ADMIN_PROMPTS);
}

/**
 * Check if user can access providers admin features
 */
export function canAccessProviders(user: User | undefined): boolean {
  return hasPermission(user, PERMISSIONS.ADMIN_PROVIDERS);
}
