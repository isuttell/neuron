import { User } from "@auth0/auth0-react"; // Import User type
import { createAsyncThunk, createSlice, PayloadAction } from "@reduxjs/toolkit";
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from "../store";
import { api } from "@/lib/api";
import { toSerializableError, isClassifiedError, type SerializableError } from "../types/error";

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

export type ConnectionStatus = 'connected' | 'connecting' | 'network_error' | 'server_error' | 'auth_error';

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
  connectionStatus: ConnectionStatus; // Track connection status
  showErrorModal: boolean; // Track if error modal should be shown
  errorModalMessage: string | null; // Error message for modal
  selectedPersonalityId: string | null; // Track selected personality
}

// Load initial state from localStorage
const loadInitialState = (): AppState => {
  const defaultState: AppState = {
    sidebar_image: "",
    api: undefined,
    protectedToolSets: undefined,
    isLoading: false,
    error: null,
    currentUser: null, // Initialize currentUser
    favoritePersonalitiesCollapsed: true, // Default to closed
    buildHashMismatch: false,
    connectionStatus: 'connecting',
    showErrorModal: false,
    errorModalMessage: null,
    selectedPersonalityId: null, // Initialize selectedPersonalityId
  };

  try {
    const savedState = localStorage.getItem(STORAGE_KEY);
    if (savedState) {
      const parsedState = JSON.parse(savedState);
      // Merge saved state with default state to handle new fields
      return {
        ...defaultState,
        ...parsedState,
      };
    }
  } catch (error) {
    console.error("Failed to load app state from localStorage:", error);
  }
  return defaultState;
};

// Save state to localStorage
const saveState = (state: AppState) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error("Failed to save app state to localStorage:", error);
  }
};

export const fetchConfig = createAsyncThunk(
  "app/fetchConfig",
  async (_, thunkAPI) => {
    try {
      return await api.get<Config>("/app/config");
    } catch (error) {
      // Convert ClassifiedError to SerializableError for Redux state
      if (isClassifiedError(error)) {
        return thunkAPI.rejectWithValue(toSerializableError(error));
      }
      // Fallback for other error types
      return thunkAPI.rejectWithValue({
        message: error instanceof Error ? error.message : "An unknown error occurred",
        type: "unknown" as const,
      });
    }
  }
);

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
    setConnectionStatus: (state, action: PayloadAction<ConnectionStatus>) => {
      state.connectionStatus = action.payload;
      // Clear error modal when connection is successful
      if (action.payload === 'connected') {
        state.showErrorModal = false;
        state.errorModalMessage = null;
      }
    },
    setErrorModal: (state, action: PayloadAction<{ show: boolean; message?: string }>) => {
      state.showErrorModal = action.payload.show;
      state.errorModalMessage = action.payload.message || null;
    },
    setSelectedPersonalityId: (state, action: PayloadAction<string | null>) => {
      state.selectedPersonalityId = action.payload;
      saveState(state);
    },
    handleApiError: (state, action: PayloadAction<SerializableError>) => {
      const error = action.payload;

      switch (error.type) {
        case 'network':
          state.connectionStatus = 'network_error';
          // Don't show modal for network errors, let toast handle it
          break;
        case 'server':
        case 'auth':
          state.connectionStatus = error.type === 'server' ? 'server_error' : 'auth_error';
          state.showErrorModal = true;
          state.errorModalMessage = error.message;
          break;
        default:
          state.connectionStatus = 'server_error';
          state.showErrorModal = true;
          state.errorModalMessage = error.message;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConfig.pending, (state) => {
        state.isLoading = true;
        state.error = null;
        state.connectionStatus = 'connecting';
      })
      .addCase(fetchConfig.fulfilled, (state, action) => {
        state.isLoading = false;
        state.sidebar_image = action.payload.sidebar_image;
        state.api = action.payload.api;
        state.protectedToolSets = action.payload.protectedToolSets;
        state.connectionStatus = 'connected';
        saveState(state);
      })
      .addCase(fetchConfig.rejected, (state, action) => {
        state.isLoading = false;
        const error = action.payload as SerializableError;
        state.error = error?.message || "Failed to fetch config";

        // Handle error classification
        if (error) {
          appSlice.caseReducers.handleApiError(state, {
            type: 'app/handleApiError',
            payload: error
          });
        } else {
          // Default to server error for config failures
          state.connectionStatus = 'server_error';
          state.showErrorModal = true;
          state.errorModalMessage = state.error;
        }
        saveState(state);
      });
  },
});

export const {
  setSidebarImage,
  setCurrentUser,
  setFavoritePersonalitiesCollapsed,
  setBuildHashMismatch,
  setConnectionStatus,
  setErrorModal,
  setSelectedPersonalityId,
  handleApiError
} = appSlice.actions;

export const getSidebarImage = (state: RootState) => state.app.sidebar_image;
export const getApiConfig = (state: RootState) => state.app.api;
export const getProtectedToolSets = (state: RootState) => state.app.protectedToolSets;
export const getConfigLoadingState = (state: RootState) => state.app.isLoading;
export const getConfigError = (state: RootState) => state.app.error;
export const getCurrentUser = (state: RootState) => state.app.currentUser;
export const getFavoritePersonalitiesCollapsed = (state: RootState) => state.app.favoritePersonalitiesCollapsed;
export const getBuildHashMismatch = (state: RootState) => state.app.buildHashMismatch;
export const getConnectionStatus = (state: RootState) => state.app.connectionStatus;
export const getSelectedPersonalityId = (state: RootState) => state.app.selectedPersonalityId;
export const getErrorModal = createSelector(
  (state: RootState) => state.app.showErrorModal,
  (state: RootState) => state.app.errorModalMessage,
  (show, message) => ({ show, message })
);

export default appSlice.reducer;
