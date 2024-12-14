import { createAsyncThunk } from "@reduxjs/toolkit";

export const fetchPersonality = createAsyncThunk(
  "personalities/fetchPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      const response = await fetch(
        `/neuron/api/personalities/${personalityId}`
      );
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const fetchPersonalities = createAsyncThunk(
  "personalities/fetchPersonalities",
  async (_, thunkAPI) => {
    try {
      const response = await fetch(`/neuron/api/personalities/`);
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

interface CreatePersonality {
  name: string;
  context: string;
  memory: string;
  description: string;
  tool_set?: string;
}

export const createPersonality = createAsyncThunk(
  "personalities/createPersonality",
  async (personality: CreatePersonality, thunkAPI) => {
    try {
      const response = await fetch(`/neuron/api/personalities/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(personality),
      });
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
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
      const response = await fetch(
        `/neuron/api/personalities/${personality.id}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: personality.name,
            context: personality.context,
            memory: personality.memory,
            tool_set: personality.tool_set,
            description: personality.description,
          }),
        }
      );
      const data = await response.json();
      return data;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);

export const deletePersonality = createAsyncThunk(
  "personalities/deletePersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      await fetch(`/neuron/api/personalities/${personalityId}`, {
        method: "DELETE",
      });
      return personalityId;
    } catch (error: any) {
      return thunkAPI.rejectWithValue(error.message);
    }
  }
);
