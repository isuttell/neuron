import { User } from "@auth0/auth0-react"; // Import User type
import { createAsyncThunk, createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import { api } from "@/lib/api";

// Constants for localStorage keys
const STORAGE_KEY = "neuron_app_settings";

interface Config {
  sidebar_image: string;
  api: {
    baseUrl: string;
    wsEndpoint: string;
  };
  protectedToolSets?: Record<string, string>;
}

// Define a type for the slice state
interface AppState {
  sidebar_image: string;
  api?: {
    baseUrl: string;
    wsEndpoint: string;
  };
  protectedToolSets?: Record<string, string>;
  isLoading: boolean;
  error: string | null;
  currentUser: User | null; // Add currentUser state
  favoritePersonalitiesCollapsed: boolean; // Add collapsed state for favorites
  buildHashMismatch: boolean; // Track if there's a build hash mismatch
}

// Load initial state from localStorage
const loadInitialState = (): AppState => {
  try {
    const savedState = localStorage.getItem(STORAGE_KEY);
    if (savedState) {
      return JSON.parse(savedState) as AppState;
    }
  } catch (error) {
    console.error("Failed to load app state from localStorage:", error);
  }
  return {
    sidebar_image: "",
    api: undefined,
    protectedToolSets: undefined,
    isLoading: false,
    error: null,
    currentUser: null, // Initialize currentUser
    favoritePersonalitiesCollapsed: true, // Default to closed
    buildHashMismatch: false,
  };
};

// Save state to localStorage
const saveState = (state: AppState) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error("Failed to save app state to localStorage:", error);
  }
};

export const fetchConfig = createAsyncThunk("app/fetchConfig", async () => {
  return await api.get<Config>("/app/config");
});

export const appSlice = createSlice({
  name: "app",
  initialState: loadInitialState(),
  reducers: {
    setSidebarImage: (state, action: PayloadAction<string>) => {
      state.sidebar_image = action.payload;
      saveState(state);
    },
    setCurrentUser: (state, action: PayloadAction<User | null>) => {
      state.currentUser = action.payload;
      // No need to save user to localStorage, Auth0 handles session
    },
    setFavoritePersonalitiesCollapsed: (state, action: PayloadAction<boolean>) => {
      state.favoritePersonalitiesCollapsed = action.payload;
      saveState(state);
    },
    setBuildHashMismatch: (state, action: PayloadAction<boolean>) => {
      state.buildHashMismatch = action.payload;
      // Don't save to localStorage - this is session-specific
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConfig.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConfig.fulfilled, (state, action) => {
        state.isLoading = false;
        state.sidebar_image = action.payload.sidebar_image;
        state.api = action.payload.api;
        state.protectedToolSets = action.payload.protectedToolSets;
        saveState(state);
      })
      .addCase(fetchConfig.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || "Failed to fetch config";
        saveState(state);
      });
  },
});

export const {
  setSidebarImage,
  setCurrentUser,
  setFavoritePersonalitiesCollapsed,
  setBuildHashMismatch
} = appSlice.actions;

export const getSidebarImage = (state: RootState) => state.app.sidebar_image;
export const getApiConfig = (state: RootState) => state.app.api;
export const getProtectedToolSets = (state: RootState) => state.app.protectedToolSets;
export const getConfigLoadingState = (state: RootState) => state.app.isLoading;
export const getConfigError = (state: RootState) => state.app.error;
export const getCurrentUser = (state: RootState) => state.app.currentUser;
export const getFavoritePersonalitiesCollapsed = (state: RootState) => state.app.favoritePersonalitiesCollapsed;
export const getBuildHashMismatch = (state: RootState) => state.app.buildHashMismatch;

export default appSlice.reducer;
