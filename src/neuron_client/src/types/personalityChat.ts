// TypeScript interfaces for personality chat functionality
import { MediaItem } from "./media";

export interface PersonalityMessage {
  id: string;
  personality_id: string;
  user_id: string | null; // null when personality is responding
  room_id: string;
  thread_id: string | null;
  content: string;
  created_at: string;
  updated_at: string;
  media_items: MediaItem[];
}

export interface PersonalityChatState {
  messageMap: Record<string, PersonalityChatMessage>;
  messageIds: string[];
  activePersonalityId: string | null;
  loading: boolean;
  error: string | null;
  // Pagination state
  hasMore: Record<string, boolean>; // Track if more messages available per personality
  loadingMore: Record<string, boolean>; // Track loading state for pagination
}

// API Request/Response types
export interface PersonalityMessagesResponse {
  personality_messages: PersonalityMessage[];
  personality: {
    id: string;
    name: string;
    description: string;
    logo?: string;
  };
  users: Array<{
    id: string;
    email: string;
    nickname: string;
    picture?: string | null;
    created_at: string;
    updated_at: string;
  }>;
}

type JsonValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | JsonValue[]
  | { [key: string]: JsonValue | undefined };

export interface CreatePersonalityMessageRequest extends Record<string, JsonValue> {
  content: string;
  room_id: string;
}

export interface UpdatePersonalityMessageRequest extends Record<string, JsonValue> {
  content: string;
}

export interface CreatePersonalityMessageResponse {
  personality_message: PersonalityMessage;
}

export interface UpdatePersonalityMessageResponse {
  personality_message: PersonalityMessage;
}

// Optimistic message interface for UI updates
export interface OptimisticPersonalityMessage extends Omit<PersonalityMessage, 'created_at' | 'updated_at'> {
  created_at: number; // timestamp for optimistic messages
  updated_at: number;
  isOptimistic?: boolean;
  tempId?: string;
  error?: string;
}

// Union type to handle both regular and optimistic messages
export type PersonalityChatMessage = PersonalityMessage | OptimisticPersonalityMessage;

// WebSocket event types (future-ready)
export interface PersonalityChatMessageEvent {
  type: "personality_chat_message";
  message: PersonalityMessage;
}

export interface PersonalityChatUpdateEvent {
  type: "personality_chat_update";
  message: PersonalityMessage;
}

export interface PersonalityChatDeleteEvent {
  type: "personality_chat_delete";
  message_id: string;
  personality_id: string;
}
