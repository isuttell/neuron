import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import { useAppSelector } from "@/hooks";
import { getConnectionStatus } from "@/slices/appSlice";
import logo from "@/assets/logo.svg";

export function ConnectionError() {
  const { logout } = useAuth0();
  const connectionStatus = useAppSelector(getConnectionStatus);

  const getTitle = () => {
    switch (connectionStatus) {
      case 'account_not_activated':
        return 'Account Not Activated';
      case 'auth_error':
        return 'Authentication Error';
      default:
        return 'Server Error';
    }
  };

  const getDescription = () => {
    switch (connectionStatus) {
      case 'account_not_activated':
        return 'Your account has not been activated yet.';
      case 'auth_error':
        return 'There was a problem with your authentication. Please log in again.';
      default:
        return 'The server is currently unavailable. Please try again later or contact support if the problem persists.';
    }
  };

  const handleRetry = () => {
    window.location.reload();
  };

  const handleLogout = () => {
    logout({ logoutParams: { returnTo: window.location.origin } });
  };

  return (
    <div className="flex flex-1 items-center justify-center h-screen w-screen">
      <div className="text-center max-w-md mx-auto p-6">
        <div className="flex justify-center mb-4">
          <img src={logo} alt="Neuron" className="size-12" />
        </div>
        <h2 className="text-xl font-semibold mb-2">
          {getTitle()}
        </h2>
        <p className="text-muted-foreground mb-6">
          {getDescription()}
        </p>
        <div className="space-y-3">
          {connectionStatus === 'account_not_activated' ? (
            <Button onClick={handleLogout} className="w-full">
              Log Out
            </Button>
          ) : connectionStatus === 'auth_error' ? (
            <Button onClick={handleLogout} className="w-full">
              Log Out
            </Button>
          ) : (
            <>
              <Button onClick={handleRetry} className="w-full">
                Retry
              </Button>
              <Button onClick={handleLogout} variant="outline" className="w-full">
                Log Out
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
