import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "@/lib/api";
import {
  SchedulerState,
  FetchEventsResponse,
  ScheduledEvent,
  RecurringPattern,
} from "./schedulerSlice.d";

const initialState: SchedulerState = {
  events: [],
  loading: false,
  error: null,
};

export const fetchEvents = createAsyncThunk<FetchEventsResponse>(
  "scheduler/fetchEvents",
  async () => {
    return await api.get("/scheduler/events");
  }
);

export const createEvent = createAsyncThunk(
  "scheduler/createEvent",
  async (eventData: {
    prompt: string;
    personality_id: string;
    thread_id?: string;
    trigger_time?: string;
    recurring_pattern?: RecurringPattern;
    additional_data?: Record<string, any>;
  }) => {
    return await api.post("/scheduler/events", eventData);
  }
);

export const deleteEvent = createAsyncThunk(
  "scheduler/deleteEvent",
  async (eventId: string) => {
    await api.delete(`/scheduler/events/${eventId}`);
    return eventId;
  }
);

export const updateEvent = createAsyncThunk(
  "scheduler/updateEvent",
  async ({
    eventId,
    eventData,
  }: {
    eventId: string;
    eventData: Partial<ScheduledEvent>;
  }) => {
    return await api.put(`/scheduler/events/${eventId}`, eventData);
  }
);

const schedulerSlice = createSlice({
  name: "scheduler",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      // Fetch events
      .addCase(fetchEvents.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.events = action.payload.events;
        state.loading = false;
      })
      .addCase(fetchEvents.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch events";
      })
      // Create event
      .addCase(createEvent.fulfilled, (state, action) => {
        state.events.push(action.payload);
      })
      // Delete event
      .addCase(deleteEvent.fulfilled, (state, action) => {
        state.events = state.events.filter(
          (event) => event.event_id !== action.payload
        );
      })
      // Update event
      .addCase(updateEvent.fulfilled, (state, action) => {
        const index = state.events.findIndex(
          (event) => event.event_id === action.payload.event_id
        );
        if (index !== -1) {
          state.events[index] = action.payload;
        }
      });
  },
});

export default schedulerSlice.reducer;
