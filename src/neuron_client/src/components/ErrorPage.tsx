import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import logo from "@/assets/logo.svg";

interface ErrorPageProps {
  errorType: 'not_found' | 'server_error' | 'auth_error' | 'network_error' | 'client_error';
  message: string;
  onBack: () => void;
}

export function ErrorPage({ errorType, message, onBack }: ErrorPageProps) {
  const { logout } = useAuth0();

  const getTitle = () => {
    switch (errorType) {
      case 'not_found':
        return 'Not Found';
      case 'auth_error':
        return 'Authentication Error';
      case 'network_error':
        return 'Connection Error';
      case 'client_error':
        return 'Access Error';
      default:
        return 'Server Error';
    }
  };

  const handleRetry = () => {
    window.location.reload();
  };

  const handleLogout = () => {
    logout({ logoutParams: { returnTo: window.location.origin } });
  };

  return (
    <div className="flex flex-1 items-center justify-center h-screen w-full">
      <div className="text-center max-w-md mx-auto p-6">
        <div className="flex justify-center mb-4">
          <img src={logo} alt="Neuron" className="size-12" />
        </div>
        <h2 className="text-xl font-semibold mb-2">
          {getTitle()}
        </h2>
        <p className="text-muted-foreground mb-6">
          {message}
        </p>
        <div className="space-y-3">
          {errorType === 'not_found' || errorType === 'client_error' ? (
            <Button onClick={onBack} className="w-full">
              Back
            </Button>
          ) : errorType === 'auth_error' ? (
            <Button onClick={handleLogout} className="w-full">
              Log Out
            </Button>
          ) : (
            <>
              <Button onClick={handleRetry} className="w-full">
                Retry
              </Button>
              <Button onClick={onBack} variant="outline" className="w-full">
                Back
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
