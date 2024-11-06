import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

interface TokenStatsPayload {
  input_tokens: number;
  output_tokens: number;
}

// Define a type for the slice state
interface AppState {
  stats: {
    inputTokenCount: number;
    outputTokenCount: number;
  };
}

// Define the initial state using that type
const initialState: AppState = {
  stats: {
    inputTokenCount: -1,
    outputTokenCount: -1,
  },
};

export const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    updateTokenStats: (state, action: PayloadAction<TokenStatsPayload>) => {
      state.stats.inputTokenCount = action.payload.input_tokens;
      state.stats.outputTokenCount = action.payload.output_tokens;
    },
  },
});

export const { updateTokenStats } = appSlice.actions;

export const getTotalInputTokens = (state: RootState) =>
  state.app.stats.inputTokenCount;
export const getTotalOutputTokens = (state: RootState) =>
  state.app.stats.outputTokenCount;

export default appSlice.reducer;
