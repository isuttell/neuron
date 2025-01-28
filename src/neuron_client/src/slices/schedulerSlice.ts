import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { api } from "@/lib/api";
type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };
import {
  SchedulerState,
  FetchEventsResponse,
  ScheduledEvent,
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

interface CreateEventRequest {
  prompt: string;
  personality_id: string;
  thread_id: string | null;
  trigger_time: string | null;
  recurring_pattern: {
    interval: number;
    unit: "seconds" | "minutes" | "hours" | "days" | "weeks" | "months";
    timeOfDay: string | null;
    dayOfWeek: number | null;
    dayOfMonth: number | null;
  } | null;
  [key: string]: JsonValue;
}

export const createEvent = createAsyncThunk<ScheduledEvent, CreateEventRequest>(
  "scheduler/createEvent",
  async (eventData) => {
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

interface UpdateEventRequest {
  eventId: string;
  eventData: {
    prompt: string | null;
    thread_id: string | null;
    personality_id: string | null;
    trigger_time: string | null;
    recurring_pattern: {
      interval: number;
      unit: "seconds" | "minutes" | "hours" | "days" | "weeks" | "months";
      timeOfDay: string | null;
      dayOfWeek: number | null;
      dayOfMonth: number | null;
    } | null;
    [key: string]: JsonValue;
  };
}

export const updateEvent = createAsyncThunk<ScheduledEvent, UpdateEventRequest>(
  "scheduler/updateEvent",
  async ({ eventId, eventData }) => {
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
      .addCase(
        createEvent.fulfilled,
        (state, action: PayloadAction<ScheduledEvent>) => {
          state.events.push(action.payload);
        }
      )
      // Delete event
      .addCase(
        deleteEvent.fulfilled,
        (state, action: PayloadAction<string>) => {
          state.events = state.events.filter(
            (event) => event.event_id !== action.payload
          );
        }
      )
      // Update event
      .addCase(
        updateEvent.fulfilled,
        (state, action: PayloadAction<ScheduledEvent>) => {
          const index = state.events.findIndex(
            (event) => event.event_id === action.payload.event_id
          );
          if (index !== -1) {
            state.events[index] = action.payload;
          }
        }
      );
  },
});

export default schedulerSlice.reducer;
