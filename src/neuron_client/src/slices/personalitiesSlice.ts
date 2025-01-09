import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/personalityActions";
import * as threadActions from "../actions/threadActions";
import * as promptsSlice from "./promptsSlice";

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
  loading: boolean;
  error: string | null;
}

// Define the initial state using that type
const initialState: PersonalityState = {
  activePersonalityId: localStorage.getItem("activePersonalityId") || undefined,
  personalities: [],
  loading: false,
  error: null,
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
      // Fetch personality
      .addCase(actions.fetchPersonality.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        actions.fetchPersonality.fulfilled,
        (state, action: PayloadAction<IncomingPersonalityEvent>) => {
          state.loading = false;
          upsert(state, action.payload.personality);
        }
      )
      .addCase(actions.fetchPersonality.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch personality";
      })
      // Fetch personalities
      .addCase(actions.fetchPersonalities.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        actions.fetchPersonalities.fulfilled,
        (state, action: PayloadAction<IncomingPersonalitiesEvent>) => {
          state.loading = false;
          state.personalities = action.payload.personalities;
        }
      )
      .addCase(actions.fetchPersonalities.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch personalities";
      })
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
      )
      .addCase(
        threadActions.fetchRecentThreads.fulfilled,
        (state, action: PayloadAction<IncomingPersonalitiesEvent>) => {
          for (const personality of action.payload.personalities) {
            upsert(state, personality);
          }
        }
      )
      .addCase(
        promptsSlice.fetchPrompts.fulfilled,
        (
          state,
          action: PayloadAction<{
            prompts: promptsSlice.Prompt[];
            personalities: Personality[];
          }>
        ) => {
          if (action.payload.personalities) {
            for (const personality of action.payload.personalities) {
              upsert(state, personality);
            }
          }
        }
      )
      .addCase(
        actions.fetchPersonalityEmbeddings.fulfilled,
        (state, action) => {
          if (action.payload.personalities) {
            for (const personality of action.payload.personalities) {
              upsert(state, personality);
            }
          }
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

export const getPersonalitiesLoading = (state: RootState) =>
  state.personalities.loading;

export const getPersonalitiesError = (state: RootState) =>
  state.personalities.error;

export default personalitiesSlice.reducer;
