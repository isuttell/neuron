import { useAuth0 } from "@auth0/auth0-react";
import { ComponentType } from "react";

export function withAdminAuth<P extends object>(
  WrappedComponent: ComponentType<P>,
  showMessage = false
) {
  return function WithAdminAuthComponent(props: P) {
    const { user } = useAuth0();
    const userRoles = (user?.["neuron/roles"] as string[]) || [];
    const isAdmin = userRoles?.includes("admin") ?? false;

    if (showMessage && !isAdmin) {
      return (
        <div className="flex flex-col items-center justify-center h-screen">
          <h1 className="text-2xl font-bold text-red-600">Access Forbidden</h1>
          <p className="text-gray-600 mt-2">
            You need administrator privileges to view this page.
          </p>
        </div>
      );
    } else if (!isAdmin) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };
}
