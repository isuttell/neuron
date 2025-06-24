import { createAsyncThunk } from "@reduxjs/toolkit";
import { Embedding } from "@/slices/embeddingsSlice";
import type { Personality, UserWithRole } from "../slices/personalitiesSlice.d";
import { api } from "@/lib/api";
import { User } from "@/types/user";

export const fetchPersonality = createAsyncThunk(
  "personalities/fetchPersonality",
  async (personalityId: string, thunkAPI) => {
    try {
      const personality = await api.get<Personality>(`/personalities/${personalityId}`);
      return { personality };
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
      const response = await api.get<{ personalities: Personality[] }>(`/personalities/`);
      return response;
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
      const createdPersonality = await api.post<Personality>(`/personalities/`, personality as unknown as Record<string, string | undefined>);
      return { personality: createdPersonality };
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
      const updatedPersonality = await api.put<Personality>(`/personalities/${personality.id}`, {
        name: personality.name,
        context: personality.context,
        memory: personality.memory,
        tool_set: personality.tool_set,
        description: personality.description,
        logo: personality.logo,
      });
      return { personality: updatedPersonality };
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
      const response = await api.post<{ personalities: Personality[]; logo: string; response: string }>(`/personalities/${personalityId}/logo`, {});
      return { personalities: response.personalities };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const fetchPersonalityUsers = createAsyncThunk(
  "personalities/fetchUsers",
  async (personalityId: string, thunkAPI) => {
    try {
      const response = await api.get<{ users: UserWithRole[] }>(`/personalities/${personalityId}/users`);
      return { personalityId, users: response.users };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const addPersonalityUser = createAsyncThunk(
  "personalities/addUser",
  async ({ personalityId, email }: { personalityId: string; email: string }, thunkAPI) => {
    try {
      // First, get the user by email
      const userResponse = await api.get<{ users: User[] }>(`/users/?email=${encodeURIComponent(email)}`);
      if (!userResponse.users || userResponse.users.length === 0) {
        throw new Error("User not found");
      }
      const user = userResponse.users[0];

      // Then add the user to the personality
      await api.post(`/personalities/${personalityId}/users`, {
        user_id: user.id,
        role: "user"
      });

      // Fetch updated users list
      const response = await api.get<{ users: UserWithRole[] }>(`/personalities/${personalityId}/users`);
      return { personalityId, users: response.users };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const updatePersonalityUserRole = createAsyncThunk(
  "personalities/updateUserRole",
  async ({ personalityId, userId, role }: { personalityId: string; userId: string; role: string }, thunkAPI) => {
    try {
      await api.put(`/personalities/${personalityId}/users/${userId}`, {
        user_id: userId,
        role
      });

      // Fetch updated users list
      const response = await api.get<{ users: UserWithRole[] }>(`/personalities/${personalityId}/users`);
      return { personalityId, users: response.users };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);

export const removePersonalityUser = createAsyncThunk(
  "personalities/removeUser",
  async ({ personalityId, userId }: { personalityId: string; userId: string }, thunkAPI) => {
    try {
      await api.delete(`/personalities/${personalityId}/users/${userId}`);

      // Fetch updated users list
      const response = await api.get<{ users: UserWithRole[] }>(`/personalities/${personalityId}/users`);
      return { personalityId, users: response.users };
    } catch (error) {
      if (error instanceof Error) {
        return thunkAPI.rejectWithValue(error.message);
      }
      return thunkAPI.rejectWithValue("An unknown error occurred");
    }
  }
);
