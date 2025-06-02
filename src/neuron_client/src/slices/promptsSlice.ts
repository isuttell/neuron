import { createAsyncThunk, createSlice, createSelector, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "../store";
import { api } from "@/lib/api";
export interface Prompt {
  id: string;
  name: string;
  text: string;
  personality_id: string | null;
  created_at: string;
  updated_at: string;
}

interface IncomingPromptEvent {
  type: "prompt";
  prompt: Prompt;
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
      ? `/prompts/?personality_id=${personalityId}`
      : "/prompts/";
    const data = await api.get<{ prompts: Prompt[]; personalities: unknown[] }>(url);
    return {
      prompts: data.prompts,
      personalities: data.personalities,
    };
  }
);

export const createPrompt = createAsyncThunk(
  "prompts/createPrompt",
  async (prompt: { name: string; text: string; personality_id?: string }) => {
    const data = await api.post<{ prompts: Prompt[] }>("/prompts/", prompt);
    return data.prompts[0];
  }
);

export const updatePrompt = createAsyncThunk(
  "prompts/updatePrompt",
  async ({ id, ...updates }: Partial<Prompt> & { id: string }) => {
    const data = await api.put<{ prompts: Prompt[] }>(`/prompts/${id}`, updates);
    return data.prompts[0];
  }
);

export const deletePrompt = createAsyncThunk(
  "prompts/deletePrompt",
  async (id: string) => {
    await api.delete(`/prompts/${id}`);
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
    upsertPrompt: (state, action: PayloadAction<IncomingPromptEvent>) => {
      state.prompts[action.payload.prompt.id] = action.payload.prompt;
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
        state.prompts = action.payload.prompts.reduce(
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

export const { clearPrompts, upsertPrompt } = promptsSlice.actions;

// Base selectors
const selectPromptsState = (state: RootState) => state.prompts;
const selectPromptsMap = (state: RootState) => state.prompts.prompts;

// Memoized selectors
export const selectPrompts = createSelector(
  [selectPromptsMap],
  (prompts) => Object.values(prompts)
);

export const selectPromptsByPersonality = createSelector(
  [selectPrompts, (_, personalityId: string) => personalityId],
  (prompts, personalityId) =>
    prompts.filter(
      (prompt) => !prompt.personality_id || prompt.personality_id === personalityId
    )
);

export const selectPromptById = createSelector(
  [selectPromptsMap, (_, id: string) => id],
  (prompts, id) => prompts[id]
);

export const selectPromptsLoading = createSelector(
  [selectPromptsState],
  (state) => state.loading
);

export const selectPromptsError = createSelector(
  [selectPromptsState],
  (state) => state.error
);

export default promptsSlice.reducer;
