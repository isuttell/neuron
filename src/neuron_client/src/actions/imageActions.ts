import { createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "@/lib/api";

interface MediaFile {
  id: string;
  path: string;
  url: string;
  prompt: string | null;
  created_at: string;
  size: number;
  mime_type: string;
  media_type: string;
}

export const fetchImages = createAsyncThunk(
  "images/fetchImages",
  async (_, thunkAPI) => {
    try {
      const data = await api.get<MediaFile[]>("/images/");
      return data;
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
