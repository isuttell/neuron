import { IncomingMessage } from "../slices/messagesSlice";
import { MediaItem } from "./media";
import { Personality } from "./personality";
import { PersonalityMessage } from "./personalityChat";
import { Thread } from "./thread";

export interface WebSocketMessage<T = unknown> {
  type: string;
  [key: string]: T | string | unknown;
}

export interface ConnectionEvent extends WebSocketMessage {
  type: "open" | "close";
}

export interface MessageEvent extends WebSocketMessage {
  type: "message";
  message: IncomingMessage;
}

export interface MediaEvent extends WebSocketMessage {
  type: "media";
  media: MediaItem[];
}

export interface PartialMessageEvent extends WebSocketMessage {
  type: "partial_message";
  message: IncomingMessage & { index: number };
}

export interface ThreadEvent extends WebSocketMessage {
  type: "thread";
  thread: Thread;
}

export interface SidebarImageEvent extends WebSocketMessage {
  type: "sidebar_image";
  url: string;
}

import { Prompt } from "../slices/promptsSlice";

export interface PromptEvent extends WebSocketMessage {
  type: "prompt";
  prompt: Prompt;
}

export interface PersonalityEvent extends WebSocketMessage {
  type: "personality";
  personality: Personality;
}

export interface PersonalityStatusUpdateEvent extends WebSocketMessage {
  type: "personality_status_update";
  personality_id: string;
  status: string;
}

export interface ImageEvent extends WebSocketMessage {
  type: "image";
  image: MediaItem;
}

export interface ErrorEvent extends WebSocketMessage {
  type: "error";
  message: string;
}

export interface PingEvent extends WebSocketMessage {
  type: "ping";
  timestamp: number;
  static_hash?: string;
}

export interface PongEvent extends WebSocketMessage {
  type: "pong";
  timestamp: number;
}

// Personality Chat WebSocket Events
export interface PersonalityChatMessageEvent extends WebSocketMessage {
  type: "personality_chat_message";
  message: PersonalityMessage;
}

export interface PersonalityChatUpdateEvent extends WebSocketMessage {
  type: "personality_chat_update";
  message: PersonalityMessage;
}

export interface PersonalityChatDeleteEvent extends WebSocketMessage {
  type: "personality_chat_delete";
  message_id: string;
  personality_id: string;
}

// Backend personality message events
export interface PersonalityMessageEvent extends WebSocketMessage {
  type: "personality_message";
  personality_id: string;
  message_id: string;
  content: string;
  user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonalityMessageDeletedEvent extends WebSocketMessage {
  type: "personality_message_deleted";
  personality_id: string;
  message_id: string;
}

// Room WebSocket Events
export interface RoomJoinedEvent extends WebSocketMessage {
  type: "room_joined";
  room_type: string;
  room_id: string;
  member_count: number;
}

export interface RoomLeftEvent extends WebSocketMessage {
  type: "room_left";
  room_type: string;
  room_id: string;
}

export interface UserJoinedRoomEvent extends WebSocketMessage {
  type: "user_joined_room";
  room_type: string;
  room_id: string;
  user_id: string;
  nickname: string;
}

export interface UserLeftRoomEvent extends WebSocketMessage {
  type: "user_left_room";
  room_type: string;
  room_id: string;
  user_id: string;
  nickname: string;
}

export type WebSocketEvent =
  | MessageEvent
  | MediaEvent
  | PartialMessageEvent
  | ThreadEvent
  | SidebarImageEvent
  | PromptEvent
  | PersonalityEvent
  | PersonalityStatusUpdateEvent
  | ImageEvent
  | ErrorEvent
  | PingEvent
  | PongEvent
  | ConnectionEvent
  | PersonalityChatMessageEvent
  | PersonalityChatUpdateEvent
  | PersonalityChatDeleteEvent
  | PersonalityMessageEvent
  | PersonalityMessageDeletedEvent
  | RoomJoinedEvent
  | RoomLeftEvent
  | UserJoinedRoomEvent
  | UserLeftRoomEvent;

export interface PostMessage extends WebSocketMessage {
  type: "PostMessage";
  thread_id: string;
  prompt?: string;
  greeting?: string;
  personality_id: string;
}

export interface CreateImageMessage extends WebSocketMessage {
  type: "CreateImage";
  prompt: string;
}

export interface DeleteThreadMessage extends WebSocketMessage {
  type: "DeleteThread";
  thread_id: string;
}

export interface DeletePersonalityMessage extends WebSocketMessage {
  type: "DeletePersonality";
  personality_id: string;
}

export interface DeleteImageMessage extends WebSocketMessage {
  type: "DeleteImage";
  image_id: string;
}

// Personality Chat WebSocket Payloads
export interface SendPersonalityChatMessage extends WebSocketMessage {
  type: "SendPersonalityChatMessage";
  personality_id: string;
  content: string;
}

export interface UpdatePersonalityChatMessage extends WebSocketMessage {
  type: "UpdatePersonalityChatMessage";
  personality_id: string;
  message_id: string;
  content: string;
}

export interface DeletePersonalityChatMessage extends WebSocketMessage {
  type: "DeletePersonalityChatMessage";
  personality_id: string;
  message_id: string;
}

// Room WebSocket Payloads
export interface JoinPersonalityRoom extends WebSocketMessage {
  type: "JoinPersonalityRoom";
  personality_id: string;
}

export interface LeavePersonalityRoom extends WebSocketMessage {
  type: "LeavePersonalityRoom";
  personality_id: string;
}


export type WebSocketPayload =
  | PostMessage
  | CreateImageMessage
  | DeleteThreadMessage
  | DeletePersonalityMessage
  | DeleteImageMessage
  | SendPersonalityChatMessage
  | UpdatePersonalityChatMessage
  | DeletePersonalityChatMessage
  | JoinPersonalityRoom
  | LeavePersonalityRoom;
