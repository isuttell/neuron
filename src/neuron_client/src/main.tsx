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
import NotFoundPage from "./not-found-page.tsx";
import Gallery from "./routes/gallery.tsx";
import Personality from "./routes/personality.tsx";
import Index from "./index.tsx";
import CodeViewer from "./routes/code-viewer.tsx";
import Prompts from "./routes/prompts.tsx";

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
          path: "gallery",
          element: <Gallery />,
        },
        {
          path: "prompts",
          element: <Prompts />,
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
