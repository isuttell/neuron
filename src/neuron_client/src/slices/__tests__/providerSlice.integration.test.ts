import { vi } from 'vitest';
import { configureStore } from "@reduxjs/toolkit";
import providerReducer, {
  fetchProviders,
  setupProvider,
  selectProviders,
  selectActiveProviderId,
} from "../providerSlice";
import type { RootState } from "@/store";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "@/lib/api";

describe("Provider Slice - Default Provider Integration", () => {
  let store: ReturnType<typeof configureStore<{ providers: ReturnType<typeof providerReducer> }>>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        providers: providerReducer,
      },
    });
    vi.clearAllMocks();
  });

  it("should handle default provider selection flow", async () => {
    // Mock providers with one marked as default
    const mockProviders = [
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
        default: true, // This is the default provider
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
    ];

    // Mock fetchProviders to return no active provider
    (api.get as vi.Mock).mockResolvedValueOnce({
      providers: mockProviders,
      active_provider_id: null, // No active provider
    });

    // Fetch providers
    await store.dispatch(fetchProviders());

    // Get state after fetch
    let state = store.getState();
    const providers = selectProviders(state as RootState);
    const activeProviderId = selectActiveProviderId(state as RootState);

    // Verify providers were loaded
    expect(providers).toHaveLength(2);
    expect(activeProviderId).toBeNull();

    // Find the default provider
    const defaultProvider = providers.find(p => p.default);
    expect(defaultProvider).toBeDefined();
    expect(defaultProvider?.id).toBe("provider-2");

    // Mock setupProvider call
    (api.post as vi.Mock).mockResolvedValueOnce({});

    // Simulate setting up the default provider
    await store.dispatch(setupProvider(defaultProvider!.id));

    // Verify the active provider was set
    state = store.getState();
    const newActiveProviderId = selectActiveProviderId(state as RootState);
    expect(newActiveProviderId).toBe("provider-2");
    expect(api.post).toHaveBeenCalledWith("/providers/provider-2/activate", {});
  });

  it("should not override existing active provider", async () => {
    // Mock providers with one marked as default
    const mockProviders = [
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

    // Mock fetchProviders to return an active provider
    (api.get as vi.Mock).mockResolvedValueOnce({
      providers: mockProviders,
      active_provider_id: "provider-1", // Already has active provider
    });

    // Fetch providers
    await store.dispatch(fetchProviders());

    // Get state after fetch
    const state = store.getState();
    const activeProviderId = selectActiveProviderId(state as RootState);

    // Verify the existing active provider is maintained
    expect(activeProviderId).toBe("provider-1");

    // setupProvider should NOT be called since there's already an active provider
    expect(api.post).not.toHaveBeenCalled();
  });
});
