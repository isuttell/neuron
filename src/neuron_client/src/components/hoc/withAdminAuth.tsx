import { useAuth0 } from "@auth0/auth0-react";
import { ComponentType } from "react";
import { isAdmin } from "@/lib/auth";

export function withAdminAuth<P extends object>(
  WrappedComponent: ComponentType<P>,
  showMessage = false
) {
  return function WithAdminAuthComponent(props: P) {
    const { user } = useAuth0();
    const userIsAdmin = isAdmin(user);

    if (showMessage && !userIsAdmin) {
      return (
        <div className="flex flex-col items-center justify-center h-screen">
          <h1 className="text-2xl font-bold text-red-600">Access Forbidden</h1>
          <p className="text-gray-600 mt-2">
            You need administrator privileges to view this page.
          </p>
        </div>
      );
    } else if (!userIsAdmin) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };
}
