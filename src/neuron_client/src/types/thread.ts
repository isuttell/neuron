export interface Thread {
  id: string;
  name: string;
  context: string;
  memory: string;
  personality_id: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ThreadResponse {
  thread: Thread;
}

export interface ThreadsResponse {
  threads: Thread[];
}
