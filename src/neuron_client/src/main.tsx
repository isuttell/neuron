import ScheduledEvents from "@/components/pages/ScheduledEvents";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { Auth0Provider, User } from "@auth0/auth0-react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { EmbeddingsView } from "./components/EmbeddingsView";
import ErrorPage from "./error-page.tsx";
import NotFoundPage from "./not-found-page.tsx";
import RecentMedia from "./routes/RecentMedia.tsx";
import CodeViewer from "./routes/code-viewer.tsx";
import Help from "./routes/help.tsx";
import Index from "./routes/index.tsx";
import MediaLists from "./routes/media-lists.tsx";
import Personalities from "./routes/personalities.tsx";
import Personality from "./routes/personality.tsx";
import PersonalityChat from "./routes/PersonalityChat.tsx";
import Privacy from "./routes/privacy.tsx";
import Prompts from "./routes/prompts.tsx";
import ProvidersPage from "./routes/providers";
import Root from "./routes/root.tsx";
import SharedMediaList from "./routes/shared-media-list";
import Chat from "./routes/thread.tsx";
import { setCurrentUser } from "./slices/appSlice"; // Import action
import { store } from "./store"; // Import store

import "./index.css";

const router = createBrowserRouter(
  [
    {
      path: "*",
      element: <NotFoundPage />,
    },
    {
      path: "/",
      element: <Root />,
      errorElement: <ErrorPage />,
      children: [
        {
          path: "share/:listId",
          element: <SharedMediaList />,
        },
        {
          path: "/",
          element: <Index />,
        },
        {
          path: "thread/:threadId",
          element: <Chat />,
        },

        {
          path: "/personalities",
          element: <Personalities />,
        },
        {
          path: "/personality/:personalityId/edit",
          element: <Personality />,
        },
        {
          path: "/personality/:personalityId/chat",
          element: <PersonalityChat />,
        },
        {
          path: "/personality/:personalityId/embeddings",
          element: <EmbeddingsView />,
        },
        {
          path: "/gallery",
          element: <RecentMedia />,
        },
        {
          path: "/prompts",
          element: <Prompts />,
        },
        {
          path: "/media-lists",
          element: <MediaLists />,
        },
        {
          path: "/scheduled",
          element: <ScheduledEvents />,
        },
        {
          path: "/providers",
          element: <ProvidersPage />,
        },
        {
          path: "/help",
          element: <Help />,
        },
        {
          path: "/privacy",
          element: <Privacy />,
        },
      ],
    },
    {
      path: "/code-viewer",
      element: <CodeViewer />,
    },
  ],
  { basename: "/" }
);

// eslint-disable-next-line react-refresh/only-export-components
const Auth0ProviderWithNavigate = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  // Make the callback async
  const onRedirectCallback = async (
    appState: { returnTo?: string } | undefined,
    user: User | undefined
  ) => {
    if (user) {
      // Dispatch user info to Redux immediately
      store.dispatch(setCurrentUser(user));

      // Backend API call moved to root.tsx useEffect
    } else {
      // Handle case where user is undefined after redirect
      store.dispatch(setCurrentUser(null));
    }
    // Navigate after API call and dispatch
    router.navigate(appState?.returnTo || window.location.pathname);
  };

  return (
    <Auth0Provider
      domain={"dev-c33mi6x6gyem2l5o.us.auth0.com"}
      clientId={"LYSbL0a44J1McAObzNLfSRdoBZ7KwfPR"}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: "https://neuron.zaks.io/api",
        scope: "openid profile email offline_access",
      }}
      onRedirectCallback={onRedirectCallback}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      {children}
    </Auth0Provider>
  );
};
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <TooltipProvider>
        <MediaPlayerProvider>
          <Auth0ProviderWithNavigate>
            <RouterProvider router={router} />
            <Toaster />
          </Auth0ProviderWithNavigate>
        </MediaPlayerProvider>
      </TooltipProvider>
    </Provider>
  </StrictMode>
);
