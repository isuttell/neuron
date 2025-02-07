import { useContext } from "react";
import { MediaPlayerContext } from "@/contexts/MediaPlayerContext";

export const useMediaPlayer = () => {
  const context = useContext(MediaPlayerContext);
  if (!context) {
    throw new Error("useMediaPlayer must be used within a MediaPlayerProvider");
  }
  return context;
};
