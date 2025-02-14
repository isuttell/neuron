import { createAsyncThunk } from "@reduxjs/toolkit";
import { getAccessToken } from "./getToken";
import { Embedding } from "@/slices/embeddingsSlice";
import type { Personality } from "../slices/personalitiesSlice.d";

export const fetchPersonality = createAsyncThunk(
  "personalities/fetchPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/personalities/${personalityId}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const data = await response.json();
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/personalities/`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const data = await response.json();
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/personalities/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(personality),
      });
      const data = await response.json();
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/personalities/${personality.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          name: personality.name,
          context: personality.context,
          memory: personality.memory,
          tool_set: personality.tool_set,
          description: personality.description,
          logo: personality.logo,
        }),
      });
      const data = await response.json();
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
      const accessToken = await getAccessToken();
      await fetch(`/api/personalities/${personalityId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
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
      const accessToken = await getAccessToken();
      const response = await fetch(
        `/api/personalities/${personalityId}/embeddings`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );
      const data = await response.json();
      return data as EmbeddingsResponse;
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
      const accessToken = await getAccessToken();
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `/api/personalities/${personalityId}/embeddings`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          body: formData,
        }
      );

      const data = await response.json();
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
      const accessToken = await getAccessToken();
      await fetch(
        `/api/personalities/${personalityId}/embeddings/${embeddingId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/personalities/${personalityId}/logo`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      const data = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
