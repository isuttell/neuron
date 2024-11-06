import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { store } from "./store";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Root from "./routes/root.tsx";
import Chat from "./routes/thread.tsx";
import Personalities from "./routes/personalities.tsx";
import ErrorPage from "./error-page.tsx";
import Image from "./routes/image.tsx";
import Gallery from "./routes/gallery.tsx";
import Providers from "./routes/providers.tsx";
import Stats from "./routes/stats.tsx";
import { socketManager } from "./WebSocketManager";
import "./index.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Root />,
    errorElement: <ErrorPage />,
    children: [
      {
        path: "thread/:threadId",
        element: <Chat />,
        loader: async ({ params: { threadId } }) => {
          socketManager.ready().then(() => {
            store.dispatch({
              type: "socket/GetThread",
              thread_id: threadId,
            });
            store.dispatch({
              type: "socket/GetThreadMessages",
              thread_id: threadId,
            });
          });
          return null;
        },
      },
      {
        path: "/",
        element: <Personalities />,
        loader: async () => {
          socketManager.ready().then(() => {
            store.dispatch({
              type: "socket/GetPersonalities",
            });
          });
          return null;
        },
      },
      {
        path: "image",
        element: <Image />,
        loader: async () => {
          socketManager.ready().then(() => {
            store.dispatch({
              type: "socket/GetImages",
            });
          });
          return null;
        },
      },
      {
        path: "gallery",
        element: <Gallery />,
        loader: async () => {
          socketManager.ready().then(() => {
            store.dispatch({
              type: "socket/GetImages",
            });
          });
          return null;
        },
      },
      {
        path: "providers",
        element: <Providers />,
        loader: async () => {
          socketManager.ready().then(() => {
            store.dispatch({
              type: "socket/GetProviders",
            });
          });
          return null;
        },
      },
      {
        path: "stats",
        element: <Stats />,
      },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <TooltipProvider>
        <RouterProvider router={router} />
        <Toaster />
      </TooltipProvider>
    </Provider>
  </StrictMode>
);
