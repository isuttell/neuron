import { configureStore } from "@reduxjs/toolkit";
import { Provider } from "../providerSlice";
import providerReducer, {
  fetchProviders,
  setupProvider,
  selectProviders,
  selectActiveProviderId,
  selectProviderById,
} from "../providerSlice";
import type { RootState } from "@/store";

// Mock the api module
jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { api } from "@/lib/api";

describe("providerSlice", () => {
  let store: ReturnType<typeof configureStore<{ providers: ReturnType<typeof providerReducer> }>>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        providers: providerReducer,
      },
    });
    jest.clearAllMocks();
  });

  it("should handle initial state", () => {
    const state = store.getState();
    expect(state.providers.providers).toEqual({});
    expect(state.providers.loading).toBe(false);
    expect(state.providers.error).toBe(null);
    expect(state.providers.activeProviderId).toBe(null);
  });

  describe("fetchProviders", () => {
    it("should fetch providers with default field", async () => {
      const mockProviders: Provider[] = [
        {
          id: "provider-1",
          model_id: "gpt-4",
          provider: "openai",
          default: false,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
        {
          id: "provider-2",
          model_id: "claude-3",
          provider: "anthropic",
          default: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ];

      (api.get as jest.Mock).mockResolvedValueOnce({
        providers: mockProviders,
        active_provider_id: "provider-1",
      });

      await store.dispatch(fetchProviders());

      const state = store.getState();
      expect(api.get).toHaveBeenCalledWith("/providers/");
      expect(state.providers.providers).toEqual({
        "provider-1": mockProviders[0],
        "provider-2": mockProviders[1],
      });
      expect(state.providers.activeProviderId).toBe("provider-1");
      expect(state.providers.loading).toBe(false);
    });

    it("should handle fetch error", async () => {
      const errorMessage = "Failed to fetch";
      (api.get as jest.Mock).mockRejectedValueOnce(new Error(errorMessage));

      await store.dispatch(fetchProviders());

      const state = store.getState();
      expect(state.providers.error).toBe(errorMessage);
      expect(state.providers.loading).toBe(false);
    });
  });

  describe("setupProvider", () => {
    it("should activate a provider", async () => {
      const providerId = "provider-1";
      (api.post as jest.Mock).mockResolvedValueOnce({});

      await store.dispatch(setupProvider(providerId));

      const state = store.getState();
      expect(api.post).toHaveBeenCalledWith(`/providers/${providerId}/activate`, {});
      expect(state.providers.activeProviderId).toBe(providerId);
    });
  });

  describe("selectors", () => {
    beforeEach(async () => {
      const mockProviders: Provider[] = [
        {
          id: "provider-1",
          model_id: "gpt-4",
          provider: "openai",
          default: false,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
        {
          id: "provider-2",
          model_id: "claude-3",
          provider: "anthropic",
          default: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ];

      (api.get as jest.Mock).mockResolvedValueOnce({
        providers: mockProviders,
        active_provider_id: "provider-1",
      });

      await store.dispatch(fetchProviders());
    });

    it("should select all providers", () => {
      const providers = selectProviders(store.getState() as RootState);
      expect(providers).toHaveLength(2);
      expect(providers[0].id).toBe("provider-1");
      expect(providers[1].id).toBe("provider-2");
    });

    it("should select active provider ID", () => {
      const activeProviderId = selectActiveProviderId(store.getState() as RootState);
      expect(activeProviderId).toBe("provider-1");
    });

    it("should select provider by ID", () => {
      const provider = selectProviderById(store.getState() as RootState, "provider-2");
      expect(provider).toEqual({
        id: "provider-2",
        model_id: "claude-3",
        provider: "anthropic",
        default: true,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      });
    });

    it("should return undefined for non-existent provider ID", () => {
      const provider = selectProviderById(store.getState() as RootState, "non-existent");
      expect(provider).toBeUndefined();
    });

    it("should identify default provider", () => {
      const providers = selectProviders(store.getState() as RootState);
      const defaultProvider = providers.find(p => p.default);
      expect(defaultProvider).toBeDefined();
      expect(defaultProvider?.id).toBe("provider-2");
      expect(defaultProvider?.provider).toBe("anthropic");
    });
  });
});
