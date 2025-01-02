import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { RootState } from "../store";

export interface Prompt {
  id: string;
  name: string;
  text: string;
  personality_id: string | null;
  created_at: string;
  updated_at: string;
}

interface PromptsState {
  prompts: Record<string, Prompt>;
  loading: boolean;
  error: string | null;
}

const initialState: PromptsState = {
  prompts: {},
  loading: false,
  error: null,
};

export const fetchPrompts = createAsyncThunk(
  "prompts/fetchPrompts",
  async (personalityId?: string) => {
    const url = personalityId
      ? `/api/prompts?personality_id=${personalityId}`
      : "/api/prompts";
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error("Failed to fetch prompts");
    }
    const data = await response.json();
    return data.prompts;
  }
);

export const createPrompt = createAsyncThunk(
  "prompts/createPrompt",
  async (prompt: { name: string; text: string; personality_id?: string }) => {
    const response = await fetch("/api/prompts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(prompt),
    });
    if (!response.ok) {
      throw new Error("Failed to create prompt");
    }
    const data = await response.json();
    return data.prompts[0];
  }
);

export const updatePrompt = createAsyncThunk(
  "prompts/updatePrompt",
  async ({ id, ...updates }: Partial<Prompt> & { id: string }) => {
    const response = await fetch(`/api/prompts/${id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      throw new Error("Failed to update prompt");
    }
    const data = await response.json();
    return data.prompts[0];
  }
);

export const deletePrompt = createAsyncThunk(
  "prompts/deletePrompt",
  async (id: string) => {
    const response = await fetch(`/api/prompts/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete prompt");
    }
    return id;
  }
);

const promptsSlice = createSlice({
  name: "prompts",
  initialState,
  reducers: {
    clearPrompts: (state) => {
      state.prompts = {};
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch prompts
      .addCase(fetchPrompts.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPrompts.fulfilled, (state, action) => {
        state.loading = false;
        state.prompts = action.payload.reduce(
          (acc: Record<string, Prompt>, prompt: Prompt) => {
            acc[prompt.id] = prompt;
            return acc;
          },
          {}
        );
      })
      .addCase(fetchPrompts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch prompts";
      })
      // Create prompt
      .addCase(createPrompt.fulfilled, (state, action) => {
        const prompt = action.payload;
        state.prompts[prompt.id] = prompt;
      })
      // Update prompt
      .addCase(updatePrompt.fulfilled, (state, action) => {
        const prompt = action.payload;
        state.prompts[prompt.id] = prompt;
      })
      // Delete prompt
      .addCase(deletePrompt.fulfilled, (state, action) => {
        const id = action.payload;
        delete state.prompts[id];
      });
  },
});

export const { clearPrompts } = promptsSlice.actions;

// Selectors
export const selectPrompts = (state: RootState) =>
  Object.values(state.prompts.prompts);
export const selectPromptsByPersonality = (
  state: RootState,
  personalityId: string
) =>
  Object.values(state.prompts.prompts).filter(
    (prompt) => prompt.personality_id === personalityId
  );
export const selectPromptById = (state: RootState, id: string) =>
  state.prompts.prompts[id];
export const selectPromptsLoading = (state: RootState) => state.prompts.loading;
export const selectPromptsError = (state: RootState) => state.prompts.error;

export default promptsSlice.reducer;
