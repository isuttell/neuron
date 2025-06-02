import { createSlice, createAsyncThunk, createSelector, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "../store";
import { api } from "@/lib/api";

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
    const data = await api.get<{
      providers: Provider[];
      active_provider_id: string | null;
    }>("/providers/");
    return {
      providers: data.providers,
      activeProviderId: data.active_provider_id,
    };
  }
);

export const setupProvider = createAsyncThunk(
  "providers/setupProvider",
  async (providerId: string) => {
    await api.post(`/providers/${providerId}/activate`, {});
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

// Base selectors
const selectProvidersState = (state: RootState) => state.providers;
const selectProvidersMap = (state: RootState) => state.providers.providers;

// Memoized selectors
export const selectActiveProviderId = createSelector(
  [selectProvidersState],
  (state) => state.activeProviderId
);

export const selectProviders = createSelector(
  [selectProvidersMap],
  (providers) => Object.values(providers)
);

export const selectProviderById = createSelector(
  [selectProvidersMap, (_, id: string) => id],
  (providers, id) => providers[id]
);

export const selectProvidersLoading = createSelector(
  [selectProvidersState],
  (state) => state.loading
);

export const selectProvidersError = createSelector(
  [selectProvidersState],
  (state) => state.error
);

export default providersSlice.reducer;
