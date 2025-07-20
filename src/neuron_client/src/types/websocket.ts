import { IncomingMessage } from "../slices/messagesSlice";
import { MediaItem } from "./media";
import { Personality } from "./personality";
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

export type WebSocketEvent =
  | MessageEvent
  | MediaEvent
  | PartialMessageEvent
  | ThreadEvent
  | SidebarImageEvent
  | PromptEvent
  | PersonalityEvent
  | ImageEvent
  | ErrorEvent
  | PingEvent
  | PongEvent
  | ConnectionEvent;

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

export type WebSocketPayload =
  | PostMessage
  | CreateImageMessage
  | DeleteThreadMessage
  | DeletePersonalityMessage
  | DeleteImageMessage;
