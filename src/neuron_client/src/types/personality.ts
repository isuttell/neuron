export interface PersonalityUser {
  user_id: string;
  personality_id: string;
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
  created_at: string;
  updated_at: string;
  personality_users?: PersonalityUser[];
}
