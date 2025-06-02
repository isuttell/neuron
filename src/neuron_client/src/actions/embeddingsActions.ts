import { createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "@/lib/api";

export const fetchEmbeddingsForPersonality = createAsyncThunk(
  "embeddings/fetchForPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      const data = await api.get(`/personalities/${personalityId}/embeddings`);
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const deleteEmbedding = createAsyncThunk(
  "embeddings/delete",
  async (embeddingId: string, thunkAPI) => {
    try {
      await api.delete(`/embeddings/${embeddingId}`);
      return embeddingId;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const bulkDeleteEmbeddings = createAsyncThunk(
  "embeddings/bulkDelete",
  async (embeddingIds: string[], thunkAPI) => {
    try {
      await api.delete(`/embeddings/bulk`, { embedding_ids: embeddingIds });
      return embeddingIds;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const updateEmbedding = createAsyncThunk(
  "embeddings/update",
  async ({ id, content }: { id: string; content: string }, thunkAPI) => {
    try {
      const data = await api.post(`/embeddings/${id}`, { content });
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
