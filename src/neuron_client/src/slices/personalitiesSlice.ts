import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/personalityActions";
import * as threadActions from "../actions/threadActions";
import * as promptsSlice from "./promptsSlice";
import * as schedulerSlice from "./schedulerSlice";
import type {
  Personality,
  IncomingPersonalityEvent,
  IncomingPersonalitiesEvent,
  PersonalityState,
} from "./personalitiesSlice.d";

// Define the initial state using that type
const initialState: PersonalityState = {
  activePersonalityId: localStorage.getItem("activePersonalityId") || undefined,
  personalities: [],
  personalityUsers: {},
  loading: false,
  error: null,
  hasInitiallyFetched: false,
};

function upsert(state: PersonalityState, personality: Personality) {
  const existingPersonalityIndex = state.personalities.findIndex(
    (per) => per.id === personality.id
  );

  if (existingPersonalityIndex !== -1) {
    // Merge with existing personality, keeping existing data for any undefined fields
    state.personalities[existingPersonalityIndex] = {
      ...state.personalities[existingPersonalityIndex],
      ...personality
    };
  } else {
    state.personalities.push(personality);
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
          state.hasInitiallyFetched = true;

          // Validate activePersonalityId after fetching personalities
          if (state.activePersonalityId) {
            const personalityExists = state.personalities.some(
              p => p.id === state.activePersonalityId
            );
            if (!personalityExists) {
              // Look for a default personality
              const defaultPersonality = state.personalities.find(p => p.default);
              if (defaultPersonality) {
                state.activePersonalityId = defaultPersonality.id;
                localStorage.setItem("activePersonalityId", defaultPersonality.id);
              } else {
                // Clear the invalid personality ID if no default exists
                state.activePersonalityId = undefined;
                localStorage.removeItem("activePersonalityId");
              }
            }
          } else {
            // No active personality, check for a default
            const defaultPersonality = state.personalities?.find(p => p.default);
            if (defaultPersonality) {
              state.activePersonalityId = defaultPersonality.id;
              localStorage.setItem("activePersonalityId", defaultPersonality.id);
            }
          }
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
        actions.generatePersonality.fulfilled,
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
      .addCase(threadActions.fetchRecentThreads.fulfilled, () => {
        // ThreadsResponse doesn't include personalities, so we don't need to handle it here
      })
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
      )
      .addCase(schedulerSlice.fetchEvents.fulfilled, (state, action) => {
        state.personalities = action.payload.personalities;
        state.loading = false;
      })
      .addCase(actions.updatePersonalityLogo.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        actions.updatePersonalityLogo.fulfilled,
        (state, action: PayloadAction<IncomingPersonalitiesEvent>) => {
          state.loading = false;
          for (const personality of action.payload.personalities) {
            upsert(state, personality);
          }
        }
      )
      .addCase(actions.updatePersonalityLogo.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to update logo";
      })
      // Fetch personality users
      .addCase(actions.fetchPersonalityUsers.fulfilled, (state, action) => {
        state.personalityUsers[action.payload.personalityId] = action.payload.users;
      })
      // Add personality user
      .addCase(actions.addPersonalityUser.fulfilled, (state, action) => {
        state.personalityUsers[action.payload.personalityId] = action.payload.users;
      })
      // Update personality user role
      .addCase(actions.updatePersonalityUserRole.fulfilled, (state, action) => {
        state.personalityUsers[action.payload.personalityId] = action.payload.users;
      })
      // Remove personality user
      .addCase(actions.removePersonalityUser.fulfilled, (state, action) => {
        state.personalityUsers[action.payload.personalityId] = action.payload.users;
      })
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
          personality?.id === state.personalities.activePersonalityId
      )
    : undefined;

export const getPersonalitiesLoading = (state: RootState) =>
  state.personalities.loading;

export const getPersonalitiesError = (state: RootState) =>
  state.personalities.error;

export const getPersonalityUsers = (state: RootState, personalityId: string) =>
  state.personalities.personalityUsers[personalityId] || [];

export default personalitiesSlice.reducer;
