import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/favoritesActions";

export interface PersonalityFavorite {
  id: string;
  personality_id: string;
  user_id: string;
  created_at: string;
}

export interface FavoritesState {
  favorites: PersonalityFavorite[];
  loading: boolean;
  error: string | null;
}

const initialState: FavoritesState = {
  favorites: [],
  loading: false,
  error: null,
};

export const favoritesSlice = createSlice({
  name: "favorites",
  initialState,
  reducers: {
    clearFavorites: (state) => {
      state.favorites = [];
    },
    addFavorite: (state, action: PayloadAction<PersonalityFavorite>) => {
      // Only add if not already present
      if (!state.favorites.find(f => f.personality_id === action.payload.personality_id)) {
        state.favorites.push(action.payload);
      }
    },
    removeFavorite: (state, action: PayloadAction<string>) => {
      state.favorites = state.favorites.filter(f => f.personality_id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch favorites
      .addCase(actions.fetchFavorites.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(actions.fetchFavorites.fulfilled, (state, action) => {
        state.loading = false;
        state.favorites = action.payload.favorites;
      })
      .addCase(actions.fetchFavorites.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch favorites";
      })
      // Add favorite
      .addCase(actions.addFavorite.fulfilled, (state, action) => {
        // Only add if not already present
        if (!state.favorites.find(f => f.personality_id === action.payload.favorite.personality_id)) {
          state.favorites.push(action.payload.favorite);
        }
      })
      // Remove favorite
      .addCase(actions.removeFavorite.fulfilled, (state, action) => {
        state.favorites = state.favorites.filter(f => f.personality_id !== action.payload.personalityId);
      })
      // Toggle favorite
      .addCase(actions.toggleFavorite.fulfilled, (state, action) => {
        if (action.payload.added) {
          // Add to favorites
          if (!state.favorites.find(f => f.personality_id === action.payload.personalityId)) {
            state.favorites.push(action.payload.favorite!);
          }
        } else {
          // Remove from favorites
          state.favorites = state.favorites.filter(f => f.personality_id !== action.payload.personalityId);
        }
      });
  },
});

export const { clearFavorites, addFavorite, removeFavorite } = favoritesSlice.actions;

// Selectors
export const getFavorites = (state: RootState): PersonalityFavorite[] =>
  state.favorites.favorites;

export const getFavoritePersonalityIds = (state: RootState): Set<string> =>
  new Set(state.favorites.favorites.map(f => f.personality_id));

export const isFavorite = (state: RootState, personalityId: string): boolean =>
  state.favorites.favorites.some(f => f.personality_id === personalityId);

export const getFavoritesLoading = (state: RootState): boolean =>
  state.favorites.loading;

export const getFavoritesError = (state: RootState): string | null =>
  state.favorites.error;

export default favoritesSlice.reducer;
