export interface MediaItem {
  id: string;
  name: string;
  description: string;
  url: string;
  media_type: string;
  thread_id?: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface IncomingMediaEvent {
  media: MediaItem[];
}
