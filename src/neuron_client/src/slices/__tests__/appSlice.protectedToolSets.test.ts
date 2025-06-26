import { describe, it, expect, beforeEach, vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { appSlice, fetchConfig, getProtectedToolSets } from "../appSlice";
import { api } from "@/lib/api";

// Mock the API
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

describe("appSlice protectedToolSets functionality", () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);

    store = configureStore({
      reducer: {
        app: appSlice.reducer,
      },
    });
  });

  describe("initial state", () => {
    it("should have protectedToolSets as undefined initially", () => {
      const state = store.getState();
      expect(state.app.protectedToolSets).toBeUndefined();
    });

    it("should load protectedToolSets from localStorage if available", async () => {
      // Clear previous mocks and set up new mock before creating store
      vi.clearAllMocks();

      const savedState = {
        sidebar_image: "test-image",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets: { homeassistant: "tool-homeassistant", kepler: "tool-kepler" },
        isLoading: false,
        error: null,
        currentUser: null,
      };

      localStorageMock.getItem.mockReturnValue(JSON.stringify(savedState));

      // Use dynamic import to re-import the slice with the mocked localStorage
      vi.resetModules();
      const { appSlice: freshAppSlice } = await import("../appSlice");

      const newStore = configureStore({
        reducer: {
          app: freshAppSlice.reducer,
        },
      });

      const state = newStore.getState();
      expect(state.app.protectedToolSets).toEqual({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });
    });
  });

  describe("fetchConfig async thunk", () => {
    it("should fetch config with protectedToolSets successfully", async () => {
      const mockConfig = {
        sidebar_image: "test-image",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets: {
          homeassistant: "tool-homeassistant",
          kepler: "tool-kepler",
        },
      };

      (api.get as jest.MockedFunction<typeof api.get>).mockResolvedValue(mockConfig);

      await store.dispatch(fetchConfig());

      const state = store.getState();
      expect(state.app.protectedToolSets).toEqual({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });
      expect(state.app.isLoading).toBe(false);
      expect(state.app.error).toBeNull();
    });

    it("should handle fetchConfig with no protectedToolSets in response", async () => {
      const mockConfig = {
        sidebar_image: "test-image",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        // No protectedToolSets field
      };

      (api.get as jest.MockedFunction<typeof api.get>).mockResolvedValue(mockConfig);

      await store.dispatch(fetchConfig());

      const state = store.getState();
      expect(state.app.protectedToolSets).toBeUndefined();
      expect(state.app.isLoading).toBe(false);
    });

    it("should handle fetchConfig failure", async () => {
      const errorMessage = "Network error";
      (api.get as jest.MockedFunction<typeof api.get>).mockRejectedValue(new Error(errorMessage));

      await store.dispatch(fetchConfig());

      const state = store.getState();
      expect(state.app.protectedToolSets).toBeUndefined();
      expect(state.app.isLoading).toBe(false);
      expect(state.app.error).toBe(errorMessage);
    });

    it("should set loading state during fetchConfig", () => {
      const mockPromise = new Promise(() => {});
      (api.get as jest.MockedFunction<typeof api.get>).mockReturnValue(mockPromise);

      store.dispatch(fetchConfig());

      const state = store.getState();
      expect(state.app.isLoading).toBe(true);
      expect(state.app.error).toBeNull();
    });
  });

  describe("getProtectedToolSets selector", () => {
    it("should return undefined when protectedToolSets is not set", () => {
      const state = store.getState();
      const protectedToolSets = getProtectedToolSets(state);
      expect(protectedToolSets).toBeUndefined();
    });

    it("should return protectedToolSets when available", () => {
      const mockProtectedToolSets = {
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
        custom: "tool-custom",
      };

      // Manually set the state for testing
      store.dispatch({
        type: "app/fetchConfig/fulfilled",
        payload: {
          sidebar_image: "test",
          api: { baseUrl: "/api", wsEndpoint: "/ws" },
          protectedToolSets: mockProtectedToolSets,
        },
      });

      const state = store.getState();
      const protectedToolSets = getProtectedToolSets(state);
      expect(protectedToolSets).toEqual(mockProtectedToolSets);
    });

    it("should return empty object when protectedToolSets is empty", () => {
      store.dispatch({
        type: "app/fetchConfig/fulfilled",
        payload: {
          sidebar_image: "test",
          api: { baseUrl: "/api", wsEndpoint: "/ws" },
          protectedToolSets: {},
        },
      });

      const state = store.getState();
      const protectedToolSets = getProtectedToolSets(state);
      expect(protectedToolSets).toEqual({});
    });
  });

  describe("localStorage integration", () => {
    it("should save protectedToolSets to localStorage when config is fetched", async () => {
      const mockConfig = {
        sidebar_image: "test-image",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets: {
          homeassistant: "tool-homeassistant",
          kepler: "tool-kepler",
        },
      };

      (api.get as jest.MockedFunction<typeof api.get>).mockResolvedValue(mockConfig);

      await store.dispatch(fetchConfig());

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "neuron_app_settings",
        expect.stringContaining("protectedToolSets")
      );

      const savedData = JSON.parse(localStorageMock.setItem.mock.calls[0][1]);
      expect(savedData.protectedToolSets).toEqual({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });
    });

    it("should save state to localStorage on fetchConfig error", async () => {
      (api.get as jest.MockedFunction<typeof api.get>).mockRejectedValue(new Error("Network error"));

      await store.dispatch(fetchConfig());

      expect(localStorageMock.setItem).toHaveBeenCalled();
    });
  });

  describe("state persistence", () => {
    it("should maintain protectedToolSets across multiple config fetches", async () => {
      // First fetch
      const firstConfig = {
        sidebar_image: "image1",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets: { homeassistant: "tool-homeassistant" },
      };

      (api.get as jest.MockedFunction<typeof api.get>).mockResolvedValue(firstConfig);
      await store.dispatch(fetchConfig());

      let state = store.getState();
      expect(state.app.protectedToolSets).toEqual({ homeassistant: "tool-homeassistant" });

      // Second fetch with different protectedToolSets
      const secondConfig = {
        sidebar_image: "image2",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets: { homeassistant: "tool-homeassistant", kepler: "tool-kepler" },
      };

      (api.get as jest.MockedFunction<typeof api.get>).mockResolvedValue(secondConfig);
      await store.dispatch(fetchConfig());

      state = store.getState();
      expect(state.app.protectedToolSets).toEqual({
        homeassistant: "tool-homeassistant",
        kepler: "tool-kepler",
      });
    });
  });

  describe("type safety", () => {
    it("should handle protectedToolSets with correct TypeScript types", async () => {
      const mockConfig = {
        sidebar_image: "test-image",
        api: { baseUrl: "/api", wsEndpoint: "/ws" },
        protectedToolSets: {
          homeassistant: "tool-homeassistant",
          kepler: "tool-kepler",
        },
      };

      (api.get as jest.MockedFunction<typeof api.get>).mockResolvedValue(mockConfig);
      await store.dispatch(fetchConfig());

      const state = store.getState();
      const protectedToolSets = getProtectedToolSets(state);

      // TypeScript should infer correct types
      if (protectedToolSets) {
        expect(typeof protectedToolSets).toBe("object");
        Object.entries(protectedToolSets).forEach(([key, value]) => {
          expect(typeof key).toBe("string");
          expect(typeof value).toBe("string");
        });
      }
    });
  });
});
