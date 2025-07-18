import { createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "@/lib/api";
import type { PersonalityFavorite } from "../slices/favoritesSlice";

export const fetchFavorites = createAsyncThunk(
  "favorites/fetchFavorites",
  async (_, thunkAPI) => {
    try {
      const response = await api.get<{ favorites: PersonalityFavorite[] }>("/favorites");
      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const addFavorite = createAsyncThunk(
  "favorites/addFavorite",
  async (personalityId: string, thunkAPI) => {
    try {
      const response = await api.post<{ favorite: PersonalityFavorite }>("/favorites", {
        personality_id: personalityId,
      });
      return response;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const removeFavorite = createAsyncThunk(
  "favorites/removeFavorite",
  async (personalityId: string, thunkAPI) => {
    try {
      await api.delete(`/favorites/${personalityId}`);
      return { personalityId };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const toggleFavorite = createAsyncThunk(
  "favorites/toggleFavorite",
  async (personalityId: string, thunkAPI) => {
    try {
      const response = await api.post<{
        added: boolean;
        favorite?: PersonalityFavorite;
      }>(`/favorites/${personalityId}/toggle`, {});
      return {
        personalityId,
        added: response.added,
        favorite: response.favorite,
      };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
