import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

export interface ProviderModel {
  id: string;
  provider: string;
  model_id: string;
}

interface IncomingProvidersEvent {
  providers: ProviderModel[];
}

interface SetActiveProviderEvent {
  provider: ProviderModel | undefined;
}

// Define a type for the slice state
interface ProviderState {
  providers: ProviderModel[];
  activeProviderId: string | undefined;
}

// Define the initial state using that type
const initialState: ProviderState = {
  providers: [],
  activeProviderId: localStorage.getItem("activeProviderId") || undefined,
};

export const providersSlice = createSlice({
  name: "providers",
  initialState,
  reducers: {
    upsertProviders: (state, action: PayloadAction<IncomingProvidersEvent>) => {
      action.payload.providers.forEach((provider) => {
        const existingProviderIndex = state.providers.findIndex(
          (p) => p.id === provider.id
        );
        if (existingProviderIndex !== -1) {
          state.providers[existingProviderIndex] = provider;
        } else {
          state.providers.push(provider);
        }
      });
    },
    setActiveProvider: (
      state,
      action: PayloadAction<SetActiveProviderEvent>
    ) => {
      state.activeProviderId = action.payload.provider?.id;
      if (state.activeProviderId) {
        localStorage.setItem("activeProviderId", state.activeProviderId);
      } else {
        localStorage.removeItem("activeProviderId");
      }
    },
  },
});

export const { upsertProviders, setActiveProvider } = providersSlice.actions;

export const getProviders = (state: RootState) => state.providers.providers;
export const getActiveProviderId = (state: RootState) =>
  state.providers.activeProviderId;

export default providersSlice.reducer;
