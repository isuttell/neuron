import { createSlice } from "@reduxjs/toolkit";
import {
  deleteEmbedding,
  bulkDeleteEmbeddings,
} from "../actions/embeddingsActions";
import { fetchPersonalityEmbeddings } from "../actions/personalityActions";
import { RootState } from "../store";

interface MetadataStats {
  total?: number;
  useful?: number;
  last_recall_at?: string;
  last_useful_at?: string;
}

type MetadataValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | MetadataStats;

export interface Embedding {
  id: string;
  collection_id: string;
  collection_name?: string;
  document: string;
  cmetadata: {
    personality_id?: string;
    user_id?: string;
    thread_id?: string;
    title?: string;
    source?: string;
    created_at?: number;
    stats?: MetadataStats;
    [key: string]: MetadataValue;
  };
}

interface EmbeddingsState {
  personality: Record<string, Embedding[]>;
  loading: boolean;
  error: string | null;
}

const initialState: EmbeddingsState = {
  personality: {},
  loading: false,
  error: null,
};

const embeddingsSlice = createSlice({
  name: "embeddings",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchPersonalityEmbeddings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchPersonalityEmbeddings.fulfilled, (state, action) => {
        state.loading = false;
        state.personality[action.meta.arg] = action.payload.embeddings;
      })
      .addCase(fetchPersonalityEmbeddings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch embeddings";
      })

      // Handle single embedding deletion
      .addCase(deleteEmbedding.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteEmbedding.fulfilled, (state, action) => {
        state.loading = false;
        // Remove the deleted embedding from all personality collections
        Object.keys(state.personality).forEach((personalityId) => {
          state.personality[personalityId] = state.personality[
            personalityId
          ].filter((embedding) => embedding.id !== action.payload);
        });
      })
      .addCase(deleteEmbedding.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to delete embedding";
      })

      // Handle bulk embedding deletion
      .addCase(bulkDeleteEmbeddings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(bulkDeleteEmbeddings.fulfilled, (state, action) => {
        state.loading = false;
        // Remove the deleted embeddings from all personality collections
        const deletedIds = new Set(action.payload);
        Object.keys(state.personality).forEach((personalityId) => {
          state.personality[personalityId] = state.personality[
            personalityId
          ].filter((embedding) => !deletedIds.has(embedding.id));
        });
      })
      .addCase(bulkDeleteEmbeddings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to delete embeddings";
      });
  },
});

export const selectEmbeddingspersonality = (
  state: RootState,
  personalityId: string
) => state.embeddings.personality[personalityId] || [];

export default embeddingsSlice.reducer;
