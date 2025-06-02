import { createAsyncThunk } from "@reduxjs/toolkit";
import { Embedding } from "@/slices/embeddingsSlice";
import type { Personality } from "../slices/personalitiesSlice.d";
import { api } from "@/lib/api";

export const fetchPersonality = createAsyncThunk(
  "personalities/fetchPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      const data = await api.get(`/personalities/${personalityId}`);
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const fetchPersonalities = createAsyncThunk(
  "personalities/fetchPersonalities",
  async (_, thunkAPI) => {
    try {
      const data = await api.get(`/personalities/`);
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

interface CreatePersonality {
  name: string;
  context: string;
  memory: string;
  description: string;
  tool_set?: string;
  logo?: string;
}

export const createPersonality = createAsyncThunk(
  "personalities/createPersonality",
  async (personality: CreatePersonality, thunkAPI) => {
    try {
      const data = await api.post(`/personalities/`, personality);
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

interface UpdatePersonality extends CreatePersonality {
  id: string;
}

export const updatePersonality = createAsyncThunk(
  "personalities/updatePersonality",
  async (personality: UpdatePersonality, thunkAPI) => {
    try {
      const data = await api.put(`/personalities/${personality.id}`, {
        name: personality.name,
        context: personality.context,
        memory: personality.memory,
        tool_set: personality.tool_set,
        description: personality.description,
        logo: personality.logo,
      });
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const deletePersonality = createAsyncThunk(
  "personalities/deletePersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      await api.delete(`/personalities/${personalityId}`);
      return personalityId;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

interface EmbeddingsResponse {
  personalities: Personality[];
  embeddings: Embedding[];
}

export const fetchPersonalityEmbeddings = createAsyncThunk(
  "personalities/fetchEmbeddings",
  async (personalityId: string, thunkAPI) => {
    try {
      const data = await api.get<EmbeddingsResponse>(
        `/personalities/${personalityId}/embeddings`
      );
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const uploadEmbeddings = createAsyncThunk(
  "personalities/uploadEmbeddings",
  async (
    { personalityId, file }: { personalityId: string; file: File },
    thunkAPI
  ) => {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const data = await api.post(
        `/personalities/${personalityId}/embeddings`,
        formData
      );
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
  "personalities/deleteEmbedding",
  async (
    {
      personalityId,
      embeddingId,
    }: { personalityId: string; embeddingId: string },
    thunkAPI
  ) => {
    try {
      await api.delete(
        `/personalities/${personalityId}/embeddings/${embeddingId}`
      );
      return { personalityId, embeddingId };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const updatePersonalityLogo = createAsyncThunk(
  "personalities/updateLogo",
  async (personalityId: string, thunkAPI) => {
    try {
      const data = await api.post(`/personalities/${personalityId}/logo`, {});
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
