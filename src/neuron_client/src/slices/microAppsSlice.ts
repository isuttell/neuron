import { createAsyncThunk, createSlice, createSelector, PayloadAction } from "@reduxjs/toolkit";
import { RootState } from "../store";
import { api } from "@/lib/api";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | JsonValue[]
  | { [key: string]: JsonValue | undefined };

export interface MicroAppAction {
  id: string;
  name: string;
  description: string;
  action_type: string;
  parameters: Record<string, unknown>;
}

export interface MicroApp {
  id: string;
  name: string;
  description: string;
  schema: Record<string, unknown>;
  display_schema: Record<string, unknown> | null;
  creator_id: string;
  actions: MicroAppAction[];
  created_at: string;
  updated_at: string;
}

export interface MicroAppDataRecord {
  id: string;
  app_id: string;
  user_id: string;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MicroAppDataResponse {
  records: MicroAppDataRecord[];
  total: number;
  limit: number;
  offset: number;
}

interface MicroAppsState {
  apps: Record<string, MicroApp>;
  data: Record<string, Record<string, MicroAppDataRecord>>; // app_id -> record_id -> record
  loading: boolean;
  error: string | null;
  loadingData: Record<string, boolean>; // app_id -> loading state
}

const initialState: MicroAppsState = {
  apps: {},
  data: {},
  loading: false,
  error: null,
  loadingData: {},
};

// Async thunks for API calls
export const fetchMicroApps = createAsyncThunk(
  "microApps/fetchApps",
  async () => {
    const data = await api.get<MicroApp[]>("/micro-apps");
    return data;
  }
);

export const createMicroApp = createAsyncThunk(
  "microApps/createApp",
  async (appData: {
    name: string;
    description: string;
    schema: Record<string, unknown>;
    display_schema?: Record<string, unknown>;
    actions?: MicroAppAction[];
  }) => {
    const data = await api.post<MicroApp>("/micro-apps", appData as unknown as Record<string, JsonValue>);
    return data;
  }
);

export const updateMicroApp = createAsyncThunk(
  "microApps/updateApp",
  async (params: {
    appId: string;
    updates: {
      name?: string;
      description?: string;
      display_schema?: Record<string, unknown>;
    };
  }) => {
    const { appId, updates } = params;
    const data = await api.put<MicroApp>(`/micro-apps/${appId}`, updates as unknown as Record<string, JsonValue>);
    return data;
  }
);

export const deleteMicroApp = createAsyncThunk(
  "microApps/deleteApp",
  async (appId: string) => {
    await api.delete(`/micro-apps/${appId}`);
    return appId;
  }
);

export const fetchMicroAppData = createAsyncThunk(
  "microApps/fetchData",
  async (params: {
    appId: string;
    limit?: number;
    offset?: number;
    filters?: Record<string, string>;
  }) => {
    const { appId, limit = 100, offset = 0, filters = {} } = params;
    const queryParams = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      ...filters,
    });
    const data = await api.get<MicroAppDataResponse>(
      `/micro-apps/${appId}/data?${queryParams}`
    );
    return { appId, ...data };
  }
);

export const createMicroAppData = createAsyncThunk(
  "microApps/createData",
  async (params: { appId: string; data: Record<string, unknown> }) => {
    const { appId, data: recordData } = params;
    const data = await api.post<MicroAppDataRecord>(
      `/micro-apps/${appId}/data`,
      { data: recordData as JsonValue }
    );
    return { appId, record: data };
  }
);

export const updateMicroAppData = createAsyncThunk(
  "microApps/updateData",
  async (params: {
    appId: string;
    recordId: string;
    data: Record<string, unknown>;
    partial?: boolean;
  }) => {
    const { appId, recordId, data: recordData, partial = false } = params;
    const data = await api.put<MicroAppDataRecord>(
      `/micro-apps/${appId}/data/${recordId}`,
      { data: recordData as JsonValue, partial }
    );
    return { appId, record: data };
  }
);

export const deleteMicroAppData = createAsyncThunk(
  "microApps/deleteData",
  async (params: { appId: string; recordId: string }) => {
    const { appId, recordId } = params;
    await api.delete(`/micro-apps/${appId}/data/${recordId}`);
    return { appId, recordId };
  }
);

const microAppsSlice = createSlice({
  name: "microApps",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    // Optimistic update for field changes
    updateRecordField: (
      state,
      action: PayloadAction<{
        appId: string;
        recordId: string;
        fieldName: string;
        value: unknown;
      }>
    ) => {
      const { appId, recordId, fieldName, value } = action.payload;
      if (state.data[appId]?.[recordId]) {
        state.data[appId][recordId].data[fieldName] = value;
        state.data[appId][recordId].updated_at = new Date().toISOString();
      }
    },
    // Revert optimistic update on error
    revertRecordUpdate: (
      state,
      action: PayloadAction<{
        appId: string;
        recordId: string;
        originalRecord: MicroAppDataRecord;
      }>
    ) => {
      const { appId, recordId, originalRecord } = action.payload;
      if (state.data[appId]) {
        state.data[appId][recordId] = originalRecord;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch apps
      .addCase(fetchMicroApps.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMicroApps.fulfilled, (state, action) => {
        state.loading = false;
        state.apps = action.payload.reduce(
          (acc: Record<string, MicroApp>, app: MicroApp) => {
            acc[app.id] = app;
            return acc;
          },
          {}
        );
      })
      .addCase(fetchMicroApps.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch micro-apps";
      })

      // Create app
      .addCase(createMicroApp.fulfilled, (state, action) => {
        state.apps[action.payload.id] = action.payload;
      })
      .addCase(createMicroApp.rejected, (state, action) => {
        state.error = action.error.message || "Failed to create micro-app";
      })

      // Update app
      .addCase(updateMicroApp.fulfilled, (state, action) => {
        state.apps[action.payload.id] = action.payload;
      })
      .addCase(updateMicroApp.rejected, (state, action) => {
        state.error = action.error.message || "Failed to update micro-app";
      })

      // Delete app
      .addCase(deleteMicroApp.fulfilled, (state, action) => {
        delete state.apps[action.payload];
        delete state.data[action.payload];
        delete state.loadingData[action.payload];
      })
      .addCase(deleteMicroApp.rejected, (state, action) => {
        state.error = action.error.message || "Failed to delete micro-app";
      })

      // Fetch data
      .addCase(fetchMicroAppData.pending, (state, action) => {
        const appId = action.meta.arg.appId;
        state.loadingData[appId] = true;
        state.error = null;
      })
      .addCase(fetchMicroAppData.fulfilled, (state, action) => {
        const { appId, records } = action.payload;
        state.loadingData[appId] = false;

        if (!state.data[appId]) {
          state.data[appId] = {};
        }

        records.forEach((record) => {
          state.data[appId][record.id] = record;
        });
      })
      .addCase(fetchMicroAppData.rejected, (state, action) => {
        const appId = action.meta.arg.appId;
        state.loadingData[appId] = false;
        // Don't set global error for individual app data loading failures
        console.warn("Fetch micro app data failed for app", appId, ":", action.error.message);
      })

      // Create data
      .addCase(createMicroAppData.fulfilled, (state, action) => {
        const { appId, record } = action.payload;
        if (!state.data[appId]) {
          state.data[appId] = {};
        }
        state.data[appId][record.id] = record;
      })
      .addCase(createMicroAppData.rejected, (_, action) => {
        // Don't set global error for form validation failures - let components handle locally
        console.warn("Create micro app data failed:", action.error.message);
      })

      // Update data
      .addCase(updateMicroAppData.fulfilled, (state, action) => {
        const { appId, record } = action.payload;
        if (state.data[appId]) {
          state.data[appId][record.id] = record;
        }
      })
      .addCase(updateMicroAppData.rejected, (_, action) => {
        // Don't set global error for form validation failures - let components handle locally
        console.warn("Update micro app data failed:", action.error.message);
      })

      // Delete data
      .addCase(deleteMicroAppData.fulfilled, (state, action) => {
        const { appId, recordId } = action.payload;
        if (state.data[appId]) {
          delete state.data[appId][recordId];
        }
      })
      .addCase(deleteMicroAppData.rejected, (_, action) => {
        // Don't set global error for delete failures - let components handle locally
        console.warn("Delete micro app data failed:", action.error.message);
      });
  },
});

// Actions
export const { clearError, updateRecordField, revertRecordUpdate } = microAppsSlice.actions;

// Selectors
export const selectMicroApps = (state: RootState) => Object.values(state.microApps.apps);

export const selectMicroApp = (appId: string) =>
  createSelector(
    (state: RootState) => state.microApps.apps[appId],
    (app) => app
  );

export const selectMicroAppData = (appId: string) =>
  createSelector(
    (state: RootState) => state.microApps.data[appId] || {},
    (data) => Object.values(data)
  );

export const selectMicroAppRecord = (appId: string, recordId: string) =>
  createSelector(
    (state: RootState) => state.microApps.data[appId]?.[recordId],
    (record) => record
  );

export const selectMicroAppsLoading = (state: RootState) => state.microApps.loading;

export const selectMicroAppDataLoading = (appId: string) =>
  createSelector(
    (state: RootState) => state.microApps.loadingData[appId] || false,
    (loading) => loading
  );

export const selectMicroAppsError = (state: RootState) => state.microApps.error;

export default microAppsSlice.reducer;
