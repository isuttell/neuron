import { configureStore } from "@reduxjs/toolkit";
import websocketMiddleware from "./middleware/websocketMiddleware";
import app from "./slices/appSlice";
import embeddingsReducer from "./slices/embeddingsSlice";
import images from "./slices/imagesSlice";
import mediaListsReducer from "./slices/mediaListsSlice";
import mediaReducer from "./slices/mediaSlice";
import messages from "./slices/messagesSlice";
import personalities from "./slices/personalitiesSlice";
import promptsReducer from "./slices/promptsSlice";
import providersReducer from "./slices/providerSlice";
import schedulerReducer from "./slices/schedulerSlice";
import socket from "./slices/socketSlice";
import threads from "./slices/threadsSlice";
import { socketManager } from "./WebSocketManager";

import usersReducer from "./slices/usersSlice";

export const store = configureStore({
  reducer: {
    app,
    messages,
    threads,
    socket,
    personalities,
    images,
    prompts: promptsReducer,
    embeddings: embeddingsReducer,
    media: mediaReducer,
    mediaLists: mediaListsReducer,
    scheduler: schedulerReducer,
    providers: providersReducer,
    users: usersReducer,
  },
  // @ts-expect-error - Redux middleware type incompatibility
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: [
          "socket/connect",
          "messages/postMessageByThread",
          "threads/createThread/pending",
          "threads/createThread/fulfilled",
          "threads/createThread/rejected",
          "messages/postMessageByThread/pending",
          "messages/postMessageByThread/fulfilled",
          "messages/postMessageByThread/rejected",
        ],
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
