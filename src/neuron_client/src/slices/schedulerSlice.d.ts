import { Personality } from "./personalitiesSlice.d";

export type RecurringPattern = {
  [K in "interval" | "unit"]: K extends "interval"
    ? number
    : "seconds" | "minutes" | "hours" | "days" | "weeks" | "months";
} & {
  timeOfDay?: string;
  dayOfWeek?: number;
  dayOfMonth?: number;
};

export interface ScheduledEvent {
  event_id: string;
  event_data: {
    prompt: string;
    thread_id?: string;
    personality_id: string;
    user_id: string;
    username: string;
    [key: string]: string | number | boolean | null | undefined;
  };
  scheduled_time: string;
  created_at: string;
  recurring_pattern?: RecurringPattern;
  time_remaining_seconds: number;
}

export interface SchedulerState {
  events: ScheduledEvent[];
  loading: boolean;
  error: string | null;
}

interface FetchEventsResponse {
  events: ScheduledEvent[];
  personalities: Personality[];
}
