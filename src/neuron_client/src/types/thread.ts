export interface ThreadUser {
  user_id: string;
  thread_id: string;
  role: string;
}

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
  thread_users?: ThreadUser[];
}

export interface ThreadResponse {
  thread: Thread;
}

export interface ThreadsResponse {
  threads: Thread[];
}
