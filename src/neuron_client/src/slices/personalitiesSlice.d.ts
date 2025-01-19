export interface Personality {
  id: string;
  name: string;
  description: string;
  context: string;
  memory: string;
  tool_set: string;
  logo?: string;
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
  loading: boolean;
  error: string | null;
}
