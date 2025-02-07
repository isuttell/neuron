import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { useAppSelector } from "../hooks";
import { getConnectionStatus } from "../slices/socketSlice";
import { Spinner } from "@/components/ui/spinner";
import { useAppDispatch } from "../hooks";
import { SidebarProvider } from "@/components/ui/sidebar";
import { MainSidebar } from "@/components/layout/MainSidebar";
import { useAuth0, withAuthenticationRequired } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import { setGetAccessTokenSilently } from "../actions/getToken";
import { fetchConfig } from "@/slices/appSlice";
import { ThreadTitleUpdater } from "@/components/ThreadTitleUpdater";
import { fetchMediaLists } from "@/slices/mediaListsSlice";

export function RootComponent() {
  const {
    loginWithRedirect,
    isAuthenticated,
    isLoading,
    error,
    getAccessTokenSilently,
    logout,
  } = useAuth0();

  const isConnected = useAppSelector(getConnectionStatus);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !error) {
      loginWithRedirect();
    } else if (!isLoading && isAuthenticated) {
      dispatch({ type: "socket/connect" });
      dispatch(fetchConfig());
      dispatch(fetchMediaLists());
    }
  }, [isAuthenticated, isLoading, dispatch, error, loginWithRedirect]);

  useEffect(() => {
    if (getAccessTokenSilently) {
      setGetAccessTokenSilently(getAccessTokenSilently);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => {
    if (error && error.message === "Invalid state") {
      // Likely old url so redirect to login
      loginWithRedirect();
    }
  }, [error, loginWithRedirect]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen max-h-screen">
        <h1 className="text-2xl font-bold">Oops!</h1>
        <p className="text-lg">Sorry, an unexpected error has occurred.</p>
        <div className="mt-6">
          <div className="font-bold text-center">{error.toString()}</div>
        </div>
        <div>
          <Button
            onClick={() =>
              logout({ logoutParams: { returnTo: window.location.origin } })
            }
          >
            Log out
          </Button>
        </div>
      </div>
    );
  }

  return (
    <SidebarProvider>
      <ThreadTitleUpdater />
      <main className="flex flex-1">
        {!isLoading && isAuthenticated && isConnected ? (
          <>
            <MainSidebar />
            <Outlet />
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center h-screen w-screen">
            <Spinner />
          </div>
        )}
      </main>
    </SidebarProvider>
  );
}

export const Root = withAuthenticationRequired(RootComponent, {
  onRedirecting: () => (
    <div className="flex flex-1 items-center justify-center h-screen w-screen">
      <Spinner />
    </div>
  ),
});

export default Root;
