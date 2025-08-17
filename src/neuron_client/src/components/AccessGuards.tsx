import { usePermissions } from "@/hooks/usePermissions";
import { Navigate } from "react-router-dom";
import { ReactNode } from "react";

interface PermissionGuardProps {
  permission: string;
  children: ReactNode;
  redirectTo?: string;
}

interface RoleGuardProps {
  role: string;
  children: ReactNode;
  redirectTo?: string;
}

/**
 * Component that protects routes/content behind permission requirements
 */
export function PermissionGuard({
  permission,
  children,
  redirectTo = "/"
}: PermissionGuardProps) {
  const { hasPermission } = usePermissions();

  if (!hasPermission(permission)) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}

/**
 * Component that protects routes/content behind role requirements
 */
export function RoleGuard({
  role,
  children,
  redirectTo = "/"
}: RoleGuardProps) {
  const { hasRole } = usePermissions();

  if (!hasRole(role)) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}

// Alias for backwards compatibility
export const BetaFeatureGuard = PermissionGuard;
