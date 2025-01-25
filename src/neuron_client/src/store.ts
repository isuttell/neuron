import { configureStore } from "@reduxjs/toolkit";
import messages from "./slices/messagesSlice";
import threads from "./slices/threadsSlice";
import websocketMiddleware from "./middleware/websocketMiddleware";
import { socketManager } from "./WebSocketManager";
import socket from "./slices/socketSlice";
import personalities from "./slices/personalitiesSlice";
import images from "./slices/imagesSlice";
import app from "./slices/appSlice";
import promptsReducer from "./slices/promptsSlice";
import embeddingsReducer from "./slices/embeddingsSlice";
import mediaReducer from "./slices/mediaSlice";
import mediaListsReducer from "./slices/mediaListsSlice";
import schedulerReducer from "./slices/schedulerSlice";
import providersReducer from "./slices/providerSlice";

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
  },
  // @ts-ignore
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
