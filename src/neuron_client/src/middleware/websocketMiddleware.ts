import { Action, Dispatch, MiddlewareAPI } from "redux";
import { toast } from "sonner";
import {
  setSidebarImage,
  setBuildHashMismatch,
} from "../slices/appSlice";
import { upsertImage } from "../slices/imagesSlice";
import { upsertMedia } from "../slices/mediaSlice";
import { partialMessage, upsertMessage } from "../slices/messagesSlice";
import { upsertPersonality } from "../slices/personalitiesSlice";
import { upsertPrompt } from "../slices/promptsSlice";
import { connect, disconnect } from "../slices/socketSlice";
import { upsertThread } from "../slices/threadsSlice";
import {
  upsertMessage as upsertPersonalityChatMessage,
  updateMessage as updatePersonalityChatMessage,
  deleteMessage as deletePersonalityChatMessage,
} from "../slices/personalityChatSlice";
import type {
  ErrorEvent,
  ImageEvent,
  MediaEvent,
  MessageEvent,
  PartialMessageEvent,
  PersonalityEvent,
  PersonalityChatMessageEvent,
  PersonalityChatUpdateEvent,
  PersonalityChatDeleteEvent,
  PersonalityMessageEvent,
  PersonalityMessageDeletedEvent,
  RoomJoinedEvent,
  RoomLeftEvent,
  UserJoinedRoomEvent,
  UserLeftRoomEvent,
  PingEvent,
  PromptEvent,
  SidebarImageEvent,
  ThreadEvent,
} from "../types/websocket";
import { getCurrentBuildHash } from "../utils/buildHash";
import WebSocketManager from "../WebSocketManager";

// Store persistent disconnection toast ID
let disconnectionToastId: string | number | undefined;

const websocketMiddleware =
  (socket: WebSocketManager) =>
  ({ dispatch }: MiddlewareAPI) =>
  (next: Dispatch<Action>) =>
  (action: Action) => {
    if (action.type === "socket/connect") {
      if (socket.connect()) {
        socket.on("message", (event: MessageEvent) => {
          dispatch(upsertMessage({ message: event.message }));
        });

        socket.on("media", (event: MediaEvent) => {
          dispatch(upsertMedia({ media: event.media }));
        });

        socket.on("partial_message", (event: PartialMessageEvent) => {
          dispatch(
            partialMessage({
              message: {
                ...event.message,
                status: event.message.status || "partial",
              },
            })
          );
        });

        socket.on("thread", (event: ThreadEvent) => {
          dispatch(upsertThread({ thread: event.thread }));
        });

        socket.on("sidebar_image", (event: SidebarImageEvent) => {
          dispatch(setSidebarImage(event.url));
        });

        socket.on("prompt", (event: PromptEvent) => {
          dispatch(upsertPrompt({ type: "prompt", prompt: event.prompt }));
        });

        socket.on("ping", (event: PingEvent) => {
          // Check if we have a static hash from the server
          if (event.static_hash) {
            const currentHash = getCurrentBuildHash();
            if (currentHash && currentHash !== event.static_hash) {
              // Hash mismatch detected - new version available
              dispatch(setBuildHashMismatch(true));
            }
          }
        });

        socket.onInternal("open", () => {
          // Dispatch an action when connected
          dispatch(connect(socket));

          // Dismiss persistent disconnection toast if it exists
          if (disconnectionToastId) {
            toast.dismiss(disconnectionToastId);
            disconnectionToastId = undefined;
          }

          toast.success("Connected", {
            duration: 1500,
          });
        });

        socket.onInternal("close", () => {
          // Dispatch an action when disconnected
          dispatch(disconnect());

          // Create persistent disconnection indicator
          disconnectionToastId = toast.warning("Disconnected", {
            description: "Attempting to reconnect...",
            duration: Infinity,
            closeButton: false,
          });
        });

        socket.onInternal("give_up", () => {
          // Update existing persistent toast to error state
          if (disconnectionToastId) {
            toast.dismiss(disconnectionToastId);
          }

          disconnectionToastId = toast.error("Connection Failed", {
            description: "Unable to reconnect after multiple attempts",
            duration: Infinity,
            closeButton: true,
          });
        });

        socket.on("personality", (event: PersonalityEvent) => {
          dispatch(upsertPersonality({ personality: event.personality }));
        });

        socket.on("image", (event: ImageEvent) => {
          const image = {
            ...event.image,
            path: event.image.url,
            prompt: "",
            size: 0,
            mime_type: "image/*",
          };
          dispatch(upsertImage({ image }));
        });

        socket.on("error", (event: ErrorEvent) => {
          console.error(`ServerError: ${event.message}`);
          toast.error("Server error", {
            description: event.message,
          });
        });

        // Personality Chat WebSocket Events
        socket.on("personality_chat_message", (event: PersonalityChatMessageEvent) => {
          dispatch(upsertPersonalityChatMessage(event));
        });

        socket.on("personality_chat_update", (event: PersonalityChatUpdateEvent) => {
          dispatch(updatePersonalityChatMessage(event));
        });

        socket.on("personality_chat_delete", (event: PersonalityChatDeleteEvent) => {
          dispatch(deletePersonalityChatMessage(event));
        });

        // New personality message events from room system
        socket.on("personality_message", (event: PersonalityMessageEvent) => {
          // Convert backend PersonalityMessageEvent to frontend PersonalityChatMessageEvent format
          const personalityChatEvent = {
            type: "personality_chat_message" as const,
            message: {
              id: event.message_id,
              personality_id: event.personality_id,
              content: event.content,
              user_id: event.user_id,
              created_at: event.created_at,
              updated_at: event.updated_at,
            }
          };
          dispatch(upsertPersonalityChatMessage(personalityChatEvent));
        });

        socket.on("personality_message_deleted", (event: PersonalityMessageDeletedEvent) => {
          // Convert backend PersonalityMessageDeletedEvent to frontend format
          const deleteEvent = {
            type: "personality_chat_delete" as const,
            message_id: event.message_id,
            personality_id: event.personality_id,
          };
          dispatch(deletePersonalityChatMessage(deleteEvent));
        });

        // Room WebSocket Events
        socket.on("room_joined", (event: RoomJoinedEvent) => {
          console.log(`Joined room: ${event.room_type}:${event.room_id} (${event.member_count} members)`);
        });

        socket.on("room_left", (event: RoomLeftEvent) => {
          console.log(`Left room: ${event.room_type}:${event.room_id}`);
        });

        socket.on("user_joined_room", (event: UserJoinedRoomEvent) => {
          console.log(`User ${event.nickname} joined room: ${event.room_type}:${event.room_id}`);
          // Could show a toast notification here if desired
        });

        socket.on("user_left_room", (event: UserLeftRoomEvent) => {
          console.log(`User ${event.nickname} left room: ${event.room_type}:${event.room_id}`);
          // Could show a toast notification here if desired
        });
      }
    } else if (socket.connected && action.type.indexOf("socket/") === 0) {
      action.type = action.type.replace("socket/", "");
      socket.sendMessage(action);
    }
    return next(action);
  };

export default websocketMiddleware;
