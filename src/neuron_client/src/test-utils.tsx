import React, { PropsWithChildren } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { RootState } from './store';
import app from "./slices/appSlice";
import embeddingsReducer from "./slices/embeddingsSlice";
import favoritesReducer from "./slices/favoritesSlice";
import images from "./slices/imagesSlice";
import mediaListsReducer from "./slices/mediaListsSlice";
import mediaReducer from "./slices/mediaSlice";
import messages from "./slices/messagesSlice";
import microAppsReducer from "./slices/microAppsSlice";
import personalities from "./slices/personalitiesSlice";
import personalityChat from "./slices/personalityChatSlice";
import personalityRoom from "./slices/personalityRoomSlice";
import promptsReducer from "./slices/promptsSlice";
import room from "./slices/roomSlice";
import providersReducer from "./slices/providerSlice";
import schedulerReducer from "./slices/schedulerSlice";
import socket from "./slices/socketSlice";
import threads from "./slices/threadsSlice";
import usersReducer from "./slices/usersSlice";

// Define the store type
type AppStore = ReturnType<typeof configureStore>;

interface ExtendedRenderOptions extends Omit<RenderOptions, 'queries'> {
  preloadedState?: Partial<RootState>;
  store?: AppStore;
}

export function renderWithProviders(
  ui: React.ReactElement,
  {
    preloadedState = {},
    store = configureStore({
      reducer: {
        app,
        messages,
        threads,
        socket,
        personalities,
        personalityChat,
        personalityRoom,
        room,
        favorites: favoritesReducer,
        images,
        prompts: promptsReducer,
        embeddings: embeddingsReducer,
        media: mediaReducer,
        mediaLists: mediaListsReducer,
        scheduler: schedulerReducer,
        providers: providersReducer,
        users: usersReducer,
        microApps: microAppsReducer,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any,
      preloadedState,
      middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
          serializableCheck: false,
        }),
    }) as AppStore,
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: PropsWithChildren): JSX.Element {
    return (
      <Provider store={store}>
        <BrowserRouter>
          <TooltipProvider>
            {children}
          </TooltipProvider>
        </BrowserRouter>
      </Provider>
    );
  }

  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}
