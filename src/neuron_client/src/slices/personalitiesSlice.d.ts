import type { User } from "../types/user";

// User with role for personality users
export interface UserWithRole extends User {
  role: string;
}

export interface Personality {
  id: string;
  name: string;
  description: string;
  context: string;
  memory: string;
  tool_set: string;
  logo?: string;
  status: string;
  default?: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncomingPersonalityEvent {
  personality: Personality;
}

export interface IncomingPersonalitiesEvent {
  personalities: Personality[];
}

// Define a type for the slice state
export interface PersonalityState {
  activePersonalityId?: string;
  personalities: Personality[];
  personalityUsers: Record<string, UserWithRole[]>; // personalityId -> users with role
  loading: boolean;
  error: string | null;
  hasInitiallyFetched: boolean;
}
