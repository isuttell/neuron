import { User } from "./user";

export interface PersonalityRoomUser {
  user_id: string;
  personality_room_id: string;
  role: string;
}

export interface PersonalityRoom {
  id: string;
  personality_id: string;
  name: string;
  type: string; // 'private' or 'shared'
  message_count: number;
  status?: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonalityRoomResponse {
  personality_room: PersonalityRoom;
  personality_room_users?: PersonalityRoomUser[];
  users?: User[];
}

export interface PersonalityRoomsResponse {
  personality_rooms: PersonalityRoom[];
  personality_room_users?: PersonalityRoomUser[];
  users?: User[];
}

type JsonValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | JsonValue[]
  | { [key: string]: JsonValue | undefined };

export interface CreatePersonalityRoomRequest extends Record<string, JsonValue> {
  name?: string;
  type?: string;
}

export interface UpdatePersonalityRoomRequest extends Record<string, JsonValue> {
  name?: string;
  type?: string;
}

export interface PersonalityRoomUserRequest extends Record<string, JsonValue> {
  user_id: string;
  role?: string;
}
