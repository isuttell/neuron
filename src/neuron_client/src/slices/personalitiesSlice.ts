import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

export interface Personality {
  id: string;
  name: string;
  context: string;
  memory: string;
  created_at: string;
  updated_at: string;
}

interface IncomingPersonalityEvent {
  personality: Personality;
}

// Define a type for the slice state
interface PersonalityState {
  activePersonalityId?: string;
  personalities: Personality[];
}

// Define the initial state using that type
const initialState: PersonalityState = {
  activePersonalityId:
    sessionStorage.getItem("activePersonalityId") || undefined,
  personalities: [],
};

export const personalitiesSlice = createSlice({
  name: "personalities",
  initialState,
  reducers: {
    setActivePersonality: (
      state,
      action: PayloadAction<string | undefined>
    ) => {
      state.activePersonalityId = action.payload;
      if (action.payload) {
        sessionStorage.setItem("activePersonalityId", action.payload);
      } else {
        sessionStorage.removeItem("activePersonalityId");
      }
    },
    upsertPersonality: (
      state,
      action: PayloadAction<IncomingPersonalityEvent>
    ) => {
      const existingPersonalityIndex = state.personalities.findIndex(
        (per) => per.id === action.payload.personality.id
      );
      const per: Personality = action.payload.personality;
      if (existingPersonalityIndex !== -1) {
        state.personalities[existingPersonalityIndex] = per;
      } else {
        state.personalities.push(per);
      }
    },
    deletePersonality: (state, action: PayloadAction<string>) => {
      state.personalities = state.personalities.filter(
        (per) => per.id !== action.payload
      );
    },
  },
});

export const { upsertPersonality, deletePersonality, setActivePersonality } =
  personalitiesSlice.actions;

export const getPersonalities = (state: RootState) =>
  state.personalities.personalities;

export const getActivePersonalityId = (state: RootState): string | undefined =>
  state.personalities.activePersonalityId;

export const getActivePersonality = (
  state: RootState
): Personality | undefined =>
  state.personalities.activePersonalityId
    ? state.personalities.personalities.find(
        (personality) =>
          personality.id === state.personalities.activePersonalityId
      )
    : undefined;

export default personalitiesSlice.reducer;
