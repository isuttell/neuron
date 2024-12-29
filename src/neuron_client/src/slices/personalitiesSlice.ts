import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/personalityActions";
export interface Personality {
  id: string;
  name: string;
  description: string;
  context: string;
  memory: string;
  tool_set: string;
  created_at: string;
  updated_at: string;
}

interface IncomingPersonalityEvent {
  personality: Personality;
}

interface IncomingPersonalitiesEvent {
  personalities: Personality[];
}

// Define a type for the slice state
interface PersonalityState {
  activePersonalityId?: string;
  personalities: Personality[];
}

// Define the initial state using that type
const initialState: PersonalityState = {
  activePersonalityId: localStorage.getItem("activePersonalityId") || undefined,
  personalities: [],
};

function upsert(state: PersonalityState, personality: Personality) {
  const existingPersonalityIndex = state.personalities.findIndex(
    (per) => per.id === personality.id
  );
  const per: Personality = personality;
  if (existingPersonalityIndex !== -1) {
    state.personalities[existingPersonalityIndex] = per;
  } else {
    state.personalities.push(per);
  }
}

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
        localStorage.setItem("activePersonalityId", action.payload);
      } else {
        localStorage.removeItem("activePersonalityId");
      }
    },
    upsertPersonality: (
      state,
      action: PayloadAction<IncomingPersonalityEvent>
    ) => {
      upsert(state, action.payload.personality);
    },
    upsertPersonalities: (
      state,
      action: PayloadAction<IncomingPersonalitiesEvent>
    ) => {
      state.personalities = action.payload.personalities;
    },
    deletePersonality: (state, action: PayloadAction<string>) => {
      state.personalities = state.personalities.filter(
        (per) => per.id !== action.payload
      );
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(
        actions.fetchPersonality.fulfilled,
        (state, action: PayloadAction<IncomingPersonalityEvent>) => {
          upsert(state, action.payload.personality);
        }
      )
      .addCase(
        actions.fetchPersonalities.fulfilled,
        (state, action: PayloadAction<IncomingPersonalitiesEvent>) => {
          state.personalities = action.payload.personalities;
        }
      )
      .addCase(
        actions.createPersonality.fulfilled,
        (state, action: PayloadAction<IncomingPersonalityEvent>) => {
          upsert(state, action.payload.personality);
        }
      )
      .addCase(
        actions.updatePersonality.fulfilled,
        (state, action: PayloadAction<IncomingPersonalityEvent>) => {
          upsert(state, action.payload.personality);
        }
      )
      .addCase(
        actions.deletePersonality.fulfilled,
        (state, action: PayloadAction<string>) => {
          state.personalities = state.personalities.filter(
            (per) => per.id !== action.payload
          );
        }
      );
  },
});

export const {
  upsertPersonality,
  upsertPersonalities,
  deletePersonality,
  setActivePersonality,
} = personalitiesSlice.actions;

export const getPersonality = (state: RootState, id: string) =>
  state.personalities.personalities.find((per) => per.id === id);

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
