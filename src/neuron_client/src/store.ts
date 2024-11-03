import { configureStore } from "@reduxjs/toolkit";
import messages from "./slices/messagesSlice";
import threads from "./slices/threadsSlice";
import websocketMiddleware from "./middleware/websocketMiddleware";
import { socketManager } from "./WebSocketManager";
import socket from "./slices/socketSlice";
import providers from "./slices/providersSlice";
import personalities from "./slices/personalitiesSlice";
import images from "./slices/imagesSlice";

export const store = configureStore({
  reducer: {
    messages,
    threads,
    socket,
    personalities,
    images,
    providers,
  },
  // @ts-ignore
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ["socket/connect"],
        // Ignore these field paths in all actions
        ignoredActionPaths: ["payload.socket"],
        // Ignore these paths in the state
        ignoredPaths: ["socket.socket"],
      },
    }).concat(websocketMiddleware(socketManager)),
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch;
