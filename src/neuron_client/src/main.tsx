import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { store } from "./store";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Auth0Provider } from "@auth0/auth0-react";
import Root from "./routes/root.tsx";
import Chat from "./routes/thread.tsx";
import Personalities from "./routes/personalities.tsx";
import ErrorPage from "./error-page.tsx";
import NotFoundPage from "./not-found-page.tsx";
import RecentMedia from "./routes/RecentMedia.tsx";
import Personality from "./routes/personality.tsx";
import Index from "./routes/index.tsx";
import CodeViewer from "./routes/code-viewer.tsx";
import Prompts from "./routes/prompts.tsx";
import { EmbeddingsView } from "./components/EmbeddingsView";
import MediaLists from "./routes/media-lists.tsx";
import ScheduledEvents from "@/components/pages/ScheduledEvents";
import ProvidersPage from "./routes/providers";
import SharedMediaList from "./routes/shared-media-list";

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
          path: "/personality/:personalityId",
          element: <Personality />,
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
      ],
    },
    {
      path: "/code-viewer",
      element: <CodeViewer />,
    },
  ],
  { basename: "/" }
);

const Auth0ProviderWithNavigate = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const onRedirectCallback = (appState: { returnTo?: string } | undefined) => {
    router.navigate(appState?.returnTo || window.location.pathname);
  };

  return (
    <Auth0Provider
      domain={"dev-c33mi6x6gyem2l5o.us.auth0.com"}
      clientId={"LYSbL0a44J1McAObzNLfSRdoBZ7KwfPR"}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: "https://neuron.zaks.io/api",
      }}
      onRedirectCallback={onRedirectCallback}
      useRefreshTokens={true}
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
