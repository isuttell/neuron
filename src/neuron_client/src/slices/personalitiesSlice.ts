import { createSlice, createSelector } from "@reduxjs/toolkit";
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
  UserWithRole,
  PersonalityDocument,
} from "./personalitiesSlice.d";
import type { PersonalityUser } from "../types/personality";

// Define the initial state using that type
const initialState: PersonalityState = {
  activePersonalityId: localStorage.getItem("activePersonalityId") || undefined,
  personalities: [],
  personalityUsers: {},
  personalityDocuments: {},
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

function groupPersonalityUsersByPersonalityId(personalityUsers: PersonalityUser[]): Record<string, PersonalityUser[]> {
  const grouped: Record<string, PersonalityUser[]> = {};
  for (const pu of personalityUsers) {
    if (!grouped[pu.personality_id]) {
      grouped[pu.personality_id] = [];
    }
    grouped[pu.personality_id].push(pu);
  }
  return grouped;
}

function convertUserWithRoleToPersonalityUser(userWithRole: UserWithRole, personalityId: string): PersonalityUser {
  return {
    user_id: userWithRole.id,
    personality_id: personalityId,
    role: userWithRole.role
  };
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
    updatePersonalityStatus: (
      state,
      action: PayloadAction<{ personalityId: string; status: string }>
    ) => {
      const personality = state.personalities.find(
        (per) => per.id === action.payload.personalityId
      );
      if (personality) {
        personality.status = action.payload.status;
      }
    },
    addPersonalityDocuments: (
      state,
      action: PayloadAction<{ personalityId: string; documents: PersonalityDocument[] }>
    ) => {
      const { personalityId, documents } = action.payload;
      if (!state.personalityDocuments[personalityId]) {
        state.personalityDocuments[personalityId] = [];
      }
      // Add the new documents to the beginning of the array
      state.personalityDocuments[personalityId] = [
        ...documents,
        ...state.personalityDocuments[personalityId]
      ];
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

          // Store personality users if provided
          if (action.payload.personality_users) {
            const grouped = groupPersonalityUsersByPersonalityId(action.payload.personality_users);
            Object.assign(state.personalityUsers, grouped);
          }
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

          // Store personality users if provided
          if (action.payload.personality_users) {
            const grouped = groupPersonalityUsersByPersonalityId(action.payload.personality_users);
            state.personalityUsers = grouped;
          }

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
        const convertedUsers = action.payload.users.map(user =>
          convertUserWithRoleToPersonalityUser(user, action.payload.personalityId)
        );
        state.personalityUsers[action.payload.personalityId] = convertedUsers;
      })
      // Add personality user
      .addCase(actions.addPersonalityUser.fulfilled, (state, action) => {
        const convertedUsers = action.payload.users.map(user =>
          convertUserWithRoleToPersonalityUser(user, action.payload.personalityId)
        );
        state.personalityUsers[action.payload.personalityId] = convertedUsers;
      })
      // Update personality user role
      .addCase(actions.updatePersonalityUserRole.fulfilled, (state, action) => {
        const convertedUsers = action.payload.users.map(user =>
          convertUserWithRoleToPersonalityUser(user, action.payload.personalityId)
        );
        state.personalityUsers[action.payload.personalityId] = convertedUsers;
      })
      // Remove personality user
      .addCase(actions.removePersonalityUser.fulfilled, (state, action) => {
        const convertedUsers = action.payload.users.map(user =>
          convertUserWithRoleToPersonalityUser(user, action.payload.personalityId)
        );
        state.personalityUsers[action.payload.personalityId] = convertedUsers;
      })
      // Fetch personality documents
      .addCase(actions.fetchPersonalityDocuments.fulfilled, (state, action) => {
        state.personalityDocuments[action.payload.personalityId] = action.payload.personality_documents;
      })
      // Delete personality document
      .addCase(actions.deletePersonalityDocument.fulfilled, (state, action) => {
        const { personalityId, documentId } = action.payload;
        if (state.personalityDocuments[personalityId]) {
          state.personalityDocuments[personalityId] = state.personalityDocuments[personalityId].filter(
            doc => doc.id !== documentId
          );
        }
      })
  },
});

export const {
  upsertPersonality,
  upsertPersonalities,
  deletePersonality,
  setActivePersonality,
  updatePersonalityStatus,
  addPersonalityDocuments,
} = personalitiesSlice.actions;

export const getPersonality = createSelector(
  [(state: RootState) => state.personalities.personalities, (_, id: string) => id],
  (personalities, id) => personalities.find((per) => per.id === id)
);

export const getPersonalities = (state: RootState) =>
  state.personalities.personalities;

export const getActivePersonalityId = (state: RootState): string | undefined =>
  state.personalities.activePersonalityId;

export const getActivePersonality = createSelector(
  [(state: RootState) => state.personalities.personalities, (state: RootState) => state.personalities.activePersonalityId],
  (personalities, activePersonalityId) =>
    activePersonalityId
      ? personalities.find((personality) => personality?.id === activePersonalityId)
      : undefined
);

export const getPersonalitiesLoading = (state: RootState) =>
  state.personalities.loading;

export const getPersonalitiesError = (state: RootState) =>
  state.personalities.error;

// Stable empty array to prevent new references
const EMPTY_USER_ARRAY: PersonalityUser[] = [];
const EMPTY_DOCUMENT_ARRAY: PersonalityDocument[] = [];

export const getPersonalityUsers = createSelector(
  [(state: RootState, personalityId: string) => state.personalities.personalityUsers[personalityId], (_, personalityId: string) => personalityId],
  (users) => users || EMPTY_USER_ARRAY
);

export const getPersonalityDocuments = createSelector(
  [(state: RootState, personalityId: string) => state.personalities.personalityDocuments[personalityId], (_, personalityId: string) => personalityId],
  (documents) => documents || EMPTY_DOCUMENT_ARRAY
);

export default personalitiesSlice.reducer;
