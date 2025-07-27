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

export interface CreatePersonalityRoomRequest {
  name: string;
  type?: string;
}

export interface UpdatePersonalityRoomRequest {
  name?: string;
  type?: string;
}

export interface PersonalityRoomUserRequest {
  user_id: string;
  role?: string;
}
