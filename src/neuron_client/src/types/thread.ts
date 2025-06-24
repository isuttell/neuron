export interface ThreadUser {
  user_id: string;
  thread_id: string;
  role: string;
}

export interface Thread {
  id: string;
  user_id: string;
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
  thread_users?: ThreadUser[];
}

export interface ThreadsResponse {
  threads: Thread[];
  thread_users?: ThreadUser[];
}
