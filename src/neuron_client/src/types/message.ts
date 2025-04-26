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
    [key: string]: number | undefined;
  };
  created_at?: string;
  node?: string;
}

export interface MessageResponse {
  messages: Message[];
  media: MediaItem[];
  threads?: Thread[];
  users?: User[];
}
