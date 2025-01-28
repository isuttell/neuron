import { createAsyncThunk } from "@reduxjs/toolkit";
import { getAccessToken } from "./getToken";

export const fetchImages = createAsyncThunk(
  "images/fetchImages",
  async (_, thunkAPI) => {
    try {
      const accessToken = await getAccessToken();
      const response = await fetch(`/api/images/`, {
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
