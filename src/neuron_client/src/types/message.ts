import { MediaItem } from "./media";
import { Thread } from "./thread";
import { User } from "./user";

export interface Message {
  id: string;
  type: "ai" | "human" | "tool" | "system";
  content:
    | Array<{
        text: string;
        type: string;
        index: number;
      }>
    | string;
  thread_id: string;
  status?: string;
  tool_calls?: Array<{
    id: string;
    type: string;
    function: {
      name: string;
      arguments: string;
    };
  }>;
  tool_call_id?: string;
  additional_kwargs?: Record<string, string | number | boolean | null>;
  response_metadata?: {
    model?: string;
    finish_reason?: string;
    [key: string]: string | number | boolean | null | undefined;
  };
  usage_metadata?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
    input_token_details?: {
      cache_creation?: number;
      cache_read?: number;
    };
  };
  created_at?: string;
  node?: string;
  artifact?: {
    type: string;
    media_type?: string;
    items?: Array<{
      id: string;
      url: string;
      caption: string;
      description?: string;
      duration?: number;
      metadata?: Record<string, unknown>;
    }>;
  };
}

// Raw message from backend - matches what API returns
export interface RawMessage {
  id: string;
  type: "ai" | "human" | "tool" | "system";
  content: Array<{
    text: string;
    type: string;
    index: number;
  }> | string;
  thread_id: string;
  status?: string;
  tool_calls?: Array<{
    id: string;
    type: string;
    function: {
      name: string;
      arguments: string;
    };
  }>;
  tool_call_id?: string;
  additional_kwargs?: Record<string, unknown>;
  response_metadata?: Record<string, unknown>;
  usage_metadata?: Record<string, unknown>;
  created_at?: string;
  node?: string;
  user_id?: string;
  artifact?: {
    type: string;
    media_type?: string;
    items?: Array<{
      id: string;
      url: string;
      caption: string;
      description?: string;
      duration?: number;
      metadata?: Record<string, unknown>;
    }>;
  };
  name?: string;
}

export interface MessageResponse {
  messages: RawMessage[];
  media: MediaItem[];
  threads?: Thread[];
  users?: User[];
  thread_users?: Array<{
    user_id: string;
    thread_id: string;
    role: string;
  }>;
}
