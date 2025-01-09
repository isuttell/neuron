import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "../store";

interface AudioState {
  showPlayer: boolean;
}

const initialState: AudioState = {
  showPlayer: false,
};

export const audioSlice = createSlice({
  name: "audio",
  initialState,
  reducers: {
    togglePlayer: (state) => {
      state.showPlayer = !state.showPlayer;
    },
  },
});

export const { togglePlayer } = audioSlice.actions;
export const getShowPlayer = (state: RootState) => state.audio.showPlayer;
export default audioSlice.reducer;
