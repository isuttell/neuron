import { createAsyncThunk } from "@reduxjs/toolkit";
import { getAccessToken } from "./getToken";

export const fetchEmbeddingsForPersonality = createAsyncThunk(
  "embeddings/fetchForPersonality",
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
      const accessToken = await getAccessToken();
      await fetch(`/api/embeddings/${embeddingId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
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
      const accessToken = await getAccessToken();
      await fetch(`/api/embeddings/bulk`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ embedding_ids: embeddingIds }),
      });
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
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/embeddings/${id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error("Failed to update embedding");
      }

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
