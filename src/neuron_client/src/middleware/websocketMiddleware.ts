import WebSocketManager from "../WebSocketManager";
import { MiddlewareAPI, Dispatch, Action } from "redux";
import { connect, disconnect } from "../slices/socketSlice";
import { upsertMessage, partialMessage } from "../slices/messagesSlice";
import { upsertThread, deleteThread } from "../slices/threadsSlice";
import {
  deletePersonality,
  upsertPersonality,
} from "../slices/personalitiesSlice";
import { upsertImage, deleteImage } from "../slices/imagesSlice";
import { upsertProviders } from "../slices/providersSlice";
interface DeleteThreadAction extends Action {
  type: "DeleteThread";
  thread_id: string;
}

interface DeletePersonalityAction extends Action {
  type: "DeletePersonality";
  personality_id: string;
}

interface DeleteImageAction extends Action {
  type: "DeleteImage";
  image_id: string;
}

const websocketMiddleware =
  (socket: WebSocketManager) =>
  ({ dispatch }: MiddlewareAPI) =>
  (next: Dispatch<Action>) =>
  (
    action:
      | Action
      | DeleteThreadAction
      | DeletePersonalityAction
      | DeleteImageAction
  ) => {
    if (action.type === "socket/connect") {
      if (socket.connect()) {
        socket.on("message", (event) => {
          dispatch(upsertMessage(event));
        });

        socket.on("partial_message", (event) => {
          dispatch(partialMessage(event));
        });

        socket.on("thread", (event) => {
          dispatch(upsertThread(event));
        });

        socket.on("open", () => {
          // Dispatch an action when connected
          dispatch(connect(socket));
        });

        socket.on("close", () => {
          // Dispatch an action when disconnected
          dispatch(disconnect());
        });

        socket.on("personality", (event) => {
          dispatch(upsertPersonality(event));
        });

        socket.on("image", (event) => {
          dispatch(upsertImage(event));
        });
        socket.on("providers", (event) => {
          dispatch(upsertProviders(event));
        });

        socket.on("error", (event) => {
          console.error(event);
        });
      }
    } else if (socket.connected && action.type.indexOf("socket/") === 0) {
      action.type = action.type.replace("socket/", "");
      socket.sendMessage(action);
      if (action.type === "DeleteThread") {
        const deleteAction = action as DeleteThreadAction;
        dispatch(deleteThread(deleteAction.thread_id));
      } else if (action.type === "DeleteUser") {
        const deleteAction = action as DeletePersonalityAction;
        dispatch(deletePersonality(deleteAction.personality_id));
      } else if (action.type === "DeleteImage") {
        const deleteAction = action as DeleteImageAction;
        dispatch(deleteImage(deleteAction));
      }
    }

    return next(action);
  };

export default websocketMiddleware;
