import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "../store";
import { getAccessToken } from "../actions/getToken";

export interface Provider {
  id: string;
  model_id: string;
  provider: string;
  created_at: string;
  updated_at: string;
}

interface IncomingProviderEvent {
  type: "provider";
  provider: Provider;
}

interface ProvidersState {
  providers: Record<string, Provider>;
  loading: boolean;
  error: string | null;
  activeProviderId: string | null;
}

const initialState: ProvidersState = {
  providers: {},
  loading: false,
  error: null,
  activeProviderId: null,
};

export const fetchProviders = createAsyncThunk(
  "providers/fetchProviders",
  async () => {
    const accessToken = await getAccessToken();
    const response = await fetch("/api/providers/", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    if (!response.ok) {
      throw new Error("Failed to fetch providers");
    }
    const data = await response.json();
    return {
      providers: data.providers,
      activeProviderId: data.active_provider_id,
    };
  }
);

export const setupProvider = createAsyncThunk(
  "providers/setupProvider",
  async (providerId: string) => {
    const accessToken = await getAccessToken();
    const response = await fetch(`/api/providers/${providerId}/setup`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    if (!response.ok) {
      throw new Error("Failed to setup provider");
    }
    return providerId;
  }
);

const providersSlice = createSlice({
  name: "providers",
  initialState,
  reducers: {
    clearProviders: (state) => {
      state.providers = {};
    },
    upsertProvider: (state, action: PayloadAction<IncomingProviderEvent>) => {
      state.providers[action.payload.provider.id] = action.payload.provider;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch providers
      .addCase(fetchProviders.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchProviders.fulfilled, (state, action) => {
        state.loading = false;
        action.payload.providers.forEach((provider: Provider) => {
          state.providers[provider.id] = provider;
        });
        state.activeProviderId = action.payload.activeProviderId;
      })
      .addCase(fetchProviders.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch providers";
      })
      .addCase(setupProvider.fulfilled, (state, action) => {
        state.activeProviderId = action.payload;
      });
  },
});

export const { clearProviders, upsertProvider } = providersSlice.actions;

export const selectActiveProviderId = (state: RootState) =>
  state.providers.activeProviderId;

// Selectors
export const selectProviders = (state: RootState) =>
  Object.values(state.providers.providers);
export const selectProviderById = (state: RootState, id: string) =>
  state.providers.providers[id];
export const selectProvidersLoading = (state: RootState) =>
  state.providers.loading;
export const selectProvidersError = (state: RootState) => state.providers.error;

export default providersSlice.reducer;
