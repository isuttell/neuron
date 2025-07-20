import { MainSidebar } from "@/components/layout/MainSidebar";
import { ThreadTitleUpdater } from "@/components/ThreadTitleUpdater";
import { Button } from "@/components/ui/button";
import { SidebarProvider } from "@/components/ui/sidebar";
import { Spinner } from "@/components/ui/spinner";
import { fetchConfig } from "@/slices/appSlice";
import { fetchMediaLists } from "@/slices/mediaListsSlice";
import { fetchProviders, setupProvider, selectProviders, selectActiveProviderId } from "@/slices/providerSlice";
import { fetchPersonalities } from "@/actions/personalityActions";
import { fetchFavorites } from "@/actions/favoritesActions";
import { useAuth0, withAuthenticationRequired } from "@auth0/auth0-react";
import { useEffect, useState } from "react"; // Import useState
import { Outlet } from "react-router-dom";
import { setGetAccessTokenSilently } from "../actions/getToken";
import { useAppDispatch, useAppSelector } from "../hooks";
import { api } from "../lib/api"; // Re-add api client import
import { isAdmin } from "../lib/auth";

export function RootComponent() {
  const {
    loginWithRedirect,
    isAuthenticated,
    isLoading,
    error,
    getAccessTokenSilently,
    logout,
    user,
  } = useAuth0();

  const dispatch = useAppDispatch();
  const [userSynced, setUserSynced] = useState(false); // Add state variable
  const providers = useAppSelector(selectProviders);
  const activeProviderId = useAppSelector(selectActiveProviderId);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !error) {
      loginWithRedirect();
    } else if (!isLoading && isAuthenticated) {
      // Set the token function first
      if (getAccessTokenSilently) {
        setGetAccessTokenSilently(getAccessTokenSilently);
      }

      // Connect socket and fetch initial data
      dispatch({ type: "socket/connect" });
      dispatch(fetchConfig());
      dispatch(fetchMediaLists());

      // Only fetch providers if user is system admin
      if (isAdmin(user)) {
        dispatch(fetchProviders());
      }

      dispatch(fetchPersonalities());
      dispatch(fetchFavorites());

      // --- Add the user sync logic here ---
      // Only sync if authenticated and not already synced
      if (isAuthenticated && !userSynced) {
        const syncUser = async () => {
          try {
            await api.post("/users/login", {}); // Call the endpoint
            setUserSynced(true); // Mark as synced
          } catch (error) {
            console.error(
              "Error calling backend /users/login endpoint:",
              error
            );
          }
        };
        syncUser();
      }
    }
  }, [
    isAuthenticated,
    isLoading,
    dispatch,
    error,
    loginWithRedirect,
    getAccessTokenSilently,
    userSynced,
    user,
  ]);

  useEffect(() => {
    if (getAccessTokenSilently) {
      setGetAccessTokenSilently(getAccessTokenSilently);
    }
  }, [getAccessTokenSilently]);

  // Set default provider if no active provider is set (only for admins)
  useEffect(() => {
    if (isAdmin(user) && providers.length > 0 && !activeProviderId) {
      const defaultProvider = providers.find(p => p.default);
      if (defaultProvider) {
        dispatch(setupProvider(defaultProvider.id));
      }
    }
  }, [user, providers, activeProviderId, dispatch]);

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

  // Check if all authentication conditions are met (removed isConnected check)
  const isFullyAuthenticated = !isLoading && isAuthenticated && userSynced;

  return (
    <SidebarProvider>
      <ThreadTitleUpdater />
      <main className="flex flex-1">
        {isFullyAuthenticated ? (
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
