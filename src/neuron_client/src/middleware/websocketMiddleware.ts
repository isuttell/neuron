import { Action, Dispatch, MiddlewareAPI } from "redux";
import { toast } from "sonner";
import {
  setSidebarImage,
  setBuildHashMismatch,
} from "../slices/appSlice";
import { upsertImage } from "../slices/imagesSlice";
import { upsertMedia } from "../slices/mediaSlice";
import { partialMessage, upsertMessage } from "../slices/messagesSlice";
import { upsertPersonality, updatePersonalityStatus } from "../slices/personalitiesSlice";
import { upsertPrompt } from "../slices/promptsSlice";
import {
  joinRoomSuccess,
  leaveRoom,
  clearAllRooms,
} from "../slices/roomSlice";
import { connect, disconnect } from "../slices/socketSlice";
import { upsertThread } from "../slices/threadsSlice";
import {
  upsertMessage as upsertPersonalityChatMessage,
  updateMessage as updatePersonalityChatMessage,
  deleteMessage as deletePersonalityChatMessage,
} from "../slices/personalityChatSlice";
import {
  handleRoomCreated,
  handleRoomUpdated,
  handleRoomDeleted,
  handleUserJoined,
  handleUserLeft,
  handleRoomStatusUpdate,
} from "../slices/personalityRoomSlice";
import { MediaItem } from "../types/media";
import type {
  ErrorEvent,
  ImageEvent,
  MediaEvent,
  MessageEvent,
  PartialMessageEvent,
  PersonalityEvent,
  PersonalityStatusUpdateEvent,
  PersonalityRoomStatusUpdateEvent,
  PersonalityChatMessageEvent,
  PersonalityChatUpdateEvent,
  PersonalityChatDeleteEvent,
  PersonalityMessageEvent,
  PersonalityMessageDeletedEvent,
  RoomJoinedEvent,
  RoomLeftEvent,
  UserJoinedRoomEvent,
  UserLeftRoomEvent,
  PersonalityRoomCreatedEvent,
  PersonalityRoomUpdatedEvent,
  PersonalityRoomDeletedEvent,
  UserJoinedPersonalityRoomEvent,
  UserLeftPersonalityRoomEvent,
  PingEvent,
  PromptEvent,
  SidebarImageEvent,
  ThreadEvent,
} from "../types/websocket";
import { getCurrentBuildHash } from "../utils/buildHash";
import { socketManager } from "../WebSocketManager";

// Store persistent disconnection toast ID
let disconnectionToastId: string | number | undefined;

const websocketMiddleware =
  ({ dispatch }: MiddlewareAPI) =>
  (next: Dispatch<Action>) =>
  (action: Action) => {
    if (action.type === "socket/connect") {
      if (socketManager.connect()) {
        socketManager.on("message", (event: MessageEvent) => {
          dispatch(upsertMessage({ message: event.message }));
        });

        socketManager.on("media", (event: MediaEvent) => {
          dispatch(upsertMedia({ media: event.media }));
        });

        socketManager.on("partial_message", (event: PartialMessageEvent) => {
          dispatch(
            partialMessage({
              message: {
                ...event.message,
                status: event.message.status || "partial",
              },
            })
          );
        });

        socketManager.on("thread", (event: ThreadEvent) => {
          dispatch(upsertThread({ thread: event.thread }));
        });

        socketManager.on("sidebar_image", (event: SidebarImageEvent) => {
          dispatch(setSidebarImage(event.url));
        });

        socketManager.on("prompt", (event: PromptEvent) => {
          dispatch(upsertPrompt({ type: "prompt", prompt: event.prompt }));
        });

        socketManager.on("ping", (event: PingEvent) => {
          // Check if we have a static hash from the server
          if (event.static_hash) {
            const currentHash = getCurrentBuildHash();
            if (currentHash && currentHash !== event.static_hash) {
              // Hash mismatch detected - new version available
              dispatch(setBuildHashMismatch(true));
            }
          }
        });

        socketManager.onInternal("open", () => {
          // Dispatch an action when connected
          dispatch(connect());

          // Dismiss persistent disconnection toast if it exists
          if (disconnectionToastId) {
            toast.dismiss(disconnectionToastId);
            disconnectionToastId = undefined;
          }

          toast.success("Connected", {
            duration: 1500,
          });
        });

        socketManager.onInternal("close", () => {
          // Dispatch an action when disconnected
          dispatch(disconnect());

          // Clear all room subscriptions on disconnect
          dispatch(clearAllRooms());

          // Create persistent disconnection indicator
          disconnectionToastId = toast.warning("Disconnected", {
            description: "Attempting to reconnect...",
            duration: Infinity,
            closeButton: false,
          });
        });

        socketManager.onInternal("give_up", () => {
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

        socketManager.on("personality", (event: PersonalityEvent) => {
          dispatch(upsertPersonality({ personality: event.personality }));
        });

        socketManager.on("personality_status_update", (event: PersonalityStatusUpdateEvent) => {
          dispatch(updatePersonalityStatus({
            personalityId: event.personality_id,
            status: event.status
          }));
        });

        socketManager.on("personality_room_status_update", (event: PersonalityRoomStatusUpdateEvent) => {
          dispatch(handleRoomStatusUpdate({
            room_id: event.room_id,
            status: event.status
          }));
        });

        socketManager.on("image", (event: ImageEvent) => {
          const image = {
            ...event.image,
            path: event.image.url,
            prompt: "",
            size: 0,
            mime_type: "image/*",
          };
          dispatch(upsertImage({ image }));
        });

        socketManager.on("error", (event: ErrorEvent) => {
          console.error(`ServerError: ${event.message}`);
          toast.error("Server error", {
            description: event.message,
          });
        });

        // Personality Chat WebSocket Events
        socketManager.on("personality_chat_message", (event: PersonalityChatMessageEvent) => {
          dispatch(upsertPersonalityChatMessage(event));
        });

        socketManager.on("personality_chat_update", (event: PersonalityChatUpdateEvent) => {
          dispatch(updatePersonalityChatMessage(event));
        });

        socketManager.on("personality_chat_delete", (event: PersonalityChatDeleteEvent) => {
          dispatch(deletePersonalityChatMessage(event));
        });

        // New personality message events from room system
        socketManager.on("personality_message", (event: PersonalityMessageEvent) => {
          // Convert backend PersonalityMessageEvent to frontend PersonalityChatMessageEvent format
          const personalityChatEvent = {
            type: "personality_chat_message" as const,
            message: {
              id: event.message_id,
              personality_id: event.personality_id,
              personality_room_id: event.room_id || "", // Default to empty string if not provided
              content: event.content,
              user_id: event.user_id,
              created_at: event.created_at,
              updated_at: event.updated_at,
              media_items: (event.media_items || []) as MediaItem[],
              thread_id: null, // Personality messages don't have threads
            }
          };
          dispatch(upsertPersonalityChatMessage(personalityChatEvent));
        });

        socketManager.on("personality_message_deleted", (event: PersonalityMessageDeletedEvent) => {
          // Convert backend PersonalityMessageDeletedEvent to frontend format
          const deleteEvent = {
            type: "personality_chat_delete" as const,
            message_id: event.message_id,
            personality_id: event.personality_id,
          };
          dispatch(deletePersonalityChatMessage(deleteEvent));
        });

        // Room WebSocket Events
        socketManager.on("room_joined", (event: RoomJoinedEvent) => {
          console.log(`Joined room: ${event.room_type}:${event.room_id} (${event.member_count} members)`);

          // Update room state
          dispatch(joinRoomSuccess({
            roomType: event.room_type,
            roomId: event.room_id,
            memberCount: event.member_count,
          }));
        });

        socketManager.on("room_left", (event: RoomLeftEvent) => {
          console.log(`Left room: ${event.room_type}:${event.room_id}`);

          // Update room state
          dispatch(leaveRoom({
            roomType: event.room_type,
            roomId: event.room_id,
          }));
        });

        socketManager.on("user_joined_room", (event: UserJoinedRoomEvent) => {
          console.log(`User ${event.nickname} joined room: ${event.room_type}:${event.room_id}`);
          // Could show a toast notification here if desired
        });

        socketManager.on("user_left_room", (event: UserLeftRoomEvent) => {
          console.log(`User ${event.nickname} left room: ${event.room_type}:${event.room_id}`);
          // Could show a toast notification here if desired
        });

        // Personality Room WebSocket Events
        socketManager.on("personality_room_created", (event: PersonalityRoomCreatedEvent) => {
          dispatch(handleRoomCreated(event));
        });

        socketManager.on("personality_room_updated", (event: PersonalityRoomUpdatedEvent) => {
          dispatch(handleRoomUpdated(event));
        });

        socketManager.on("personality_room_deleted", (event: PersonalityRoomDeletedEvent) => {
          dispatch(handleRoomDeleted(event));
        });

        socketManager.on("user_joined_personality_room", (event: UserJoinedPersonalityRoomEvent) => {
          dispatch(handleUserJoined(event));
        });

        socketManager.on("user_left_personality_room", (event: UserLeftPersonalityRoomEvent) => {
          dispatch(handleUserLeft(event));
        });
      }
    } else if (socketManager.connected && action.type.indexOf("socket/") === 0) {
      action.type = action.type.replace("socket/", "");
      socketManager.sendMessage(action);
    }
    return next(action);
  };

export default websocketMiddleware;
