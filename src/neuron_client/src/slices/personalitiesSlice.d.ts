import type { User } from "../types/user";
import type { PersonalityUser } from "../types/personality";

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

export interface PersonalityDocument {
  id: string;
  personality_id: string;
  user_id: string;
  name: string;
  content: string;
  doc_metadata: {
    chunk_ids?: string[];
  };
  created_at: string;
}

export interface IncomingPersonalityEvent {
  personality: Personality;
  users?: User[];
  personality_users?: PersonalityUser[];
}

export interface IncomingPersonalitiesEvent {
  personalities: Personality[];
  users?: User[];
  personality_users?: PersonalityUser[];
}

export interface IncomingPersonalityDocumentsEvent {
  personality_documents: PersonalityDocument[];
}

export interface IncomingPersonalityDocumentEvent {
  personality_documents: PersonalityDocument[];
}

// Define a type for the slice state
export interface PersonalityState {
  activePersonalityId?: string;
  personalities: Personality[];
  personalityUsers: Record<string, PersonalityUser[]>; // personalityId -> personality user relationships
  personalityDocuments: Record<string, PersonalityDocument[]>; // personalityId -> documents
  loading: boolean;
  error: string | null;
  hasInitiallyFetched: boolean;
}
