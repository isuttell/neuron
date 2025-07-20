import { vi } from 'vitest';
import { configureStore } from "@reduxjs/toolkit";
import personalitiesReducer from "@/slices/personalitiesSlice";
import { api } from "@/lib/api";
import {
  fetchPersonalities,
  fetchPersonality,
  createPersonality,
  updatePersonality,
  deletePersonality,
  fetchPersonalityEmbeddings,
  updatePersonalityLogo,
} from "../personalityActions";
import type { Personality, PersonalityState } from "@/slices/personalitiesSlice.d";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("personalityActions", () => {
  let store: ReturnType<typeof configureStore<{ personalities: PersonalityState }>>;

  const mockPersonality: Personality = {
    id: "123e4567-e89b-12d3-a456-426614174000",
    name: "Test Personality",
    description: "A test personality",
    context: "Test context",
    memory: "Test memory",
    logo: "test-logo.png",
    tool_set: "default",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    store = configureStore({
      reducer: {
        personalities: personalitiesReducer,
      },
    });
  });

  describe("fetchPersonalities", () => {
    it("should handle successful fetch with correct response structure", async () => {
      const mockResponse = { personalities: [mockPersonality] };
      (api.get as vi.Mock).mockResolvedValueOnce(mockResponse);

      await store.dispatch(fetchPersonalities());

      expect(api.get).toHaveBeenCalledWith("/personalities/");

      const state = store.getState();
      expect(state.personalities.personalities).toHaveLength(1);
      expect(state.personalities.personalities[0]).toEqual(mockPersonality);
      expect(state.personalities.loading).toBe(false);
      expect(state.personalities.error).toBeNull();
    });

    it("should handle empty personalities array", async () => {
      const mockResponse = { personalities: [] };
      (api.get as vi.Mock).mockResolvedValueOnce(mockResponse);

      await store.dispatch(fetchPersonalities());

      const state = store.getState();
      expect(state.personalities.personalities).toHaveLength(0);
    });

    it("should handle API errors", async () => {
      const errorMessage = "Failed to fetch personalities";
      (api.get as vi.Mock).mockRejectedValueOnce(new Error(errorMessage));

      await store.dispatch(fetchPersonalities());

      const state = store.getState();
      expect(state.personalities.loading).toBe(false);
      // The error comes from Redux Toolkit's default rejection handling
      expect(state.personalities.error).toBe("Rejected");
    });
  });

  describe("fetchPersonality", () => {
    it("should handle successful fetch of single personality", async () => {
      (api.get as vi.Mock).mockResolvedValueOnce({ personality: mockPersonality });

      await store.dispatch(fetchPersonality(mockPersonality.id));

      expect(api.get).toHaveBeenCalledWith(`/personalities/${mockPersonality.id}`);

      const state = store.getState();
      expect(state.personalities.personalities).toHaveLength(1);
      expect(state.personalities.personalities[0]).toEqual(mockPersonality);
    });
  });

  describe("createPersonality", () => {
    it("should handle successful personality creation", async () => {
      const createPayload = {
        name: "New Personality",
        context: "New context",
        memory: "New memory",
        description: "New description",
      };

      (api.post as vi.Mock).mockResolvedValueOnce(mockPersonality);

      await store.dispatch(createPersonality(createPayload));

      expect(api.post).toHaveBeenCalledWith("/personalities/", createPayload);
    });
  });

  describe("updatePersonality", () => {
    it("should handle successful personality update", async () => {
      const updatePayload = {
        id: mockPersonality.id,
        name: "Updated Name",
        context: "Updated context",
        memory: "Updated memory",
        description: "Updated description",
        tool_set: "advanced",
        logo: "updated-logo.png",
      };

      const updatedPersonality = { ...mockPersonality, ...updatePayload };
      (api.put as vi.Mock).mockResolvedValueOnce({ personality: updatedPersonality });

      await store.dispatch(updatePersonality(updatePayload));

      expect(api.put).toHaveBeenCalledWith(
        `/personalities/${mockPersonality.id}`,
        {
          name: updatePayload.name,
          context: updatePayload.context,
          memory: updatePayload.memory,
          tool_set: updatePayload.tool_set,
          description: updatePayload.description,
          logo: updatePayload.logo,
        }
      );
    });
  });

  describe("deletePersonality", () => {
    it("should handle successful personality deletion", async () => {
      (api.delete as vi.Mock).mockResolvedValueOnce(undefined);

      await store.dispatch(deletePersonality(mockPersonality.id));

      expect(api.delete).toHaveBeenCalledWith(`/personalities/${mockPersonality.id}`);
    });
  });

  describe("fetchPersonalityEmbeddings", () => {
    it("should handle successful embeddings fetch", async () => {
      const mockEmbeddings = {
        personalities: [mockPersonality],
        embeddings: [
          {
            id: "embed-123",
            content: "Test content",
            metadata: { personality_id: mockPersonality.id },
            created_at: "2024-01-01T00:00:00Z",
          },
        ],
      };

      (api.get as vi.Mock).mockResolvedValueOnce(mockEmbeddings);

      await store.dispatch(
        fetchPersonalityEmbeddings(mockPersonality.id)
      );

      expect(api.get).toHaveBeenCalledWith(
        `/personalities/${mockPersonality.id}/embeddings`
      );
    });
  });

  describe("updatePersonalityLogo", () => {
    it("should handle successful logo update with correct response structure", async () => {
      const mockResponse = {
        personalities: [mockPersonality],
        logo: "new-logo.png",
        response: "Logo updated successfully",
      };

      (api.post as vi.Mock).mockResolvedValueOnce(mockResponse);

      await store.dispatch(updatePersonalityLogo(mockPersonality.id));

      expect(api.post).toHaveBeenCalledWith(
        `/personalities/${mockPersonality.id}/logo`,
        {}
      );

      const state = store.getState();
      expect(state.personalities.personalities).toHaveLength(1);
      expect(state.personalities.personalities[0]).toEqual(mockPersonality);
    });
  });
});
