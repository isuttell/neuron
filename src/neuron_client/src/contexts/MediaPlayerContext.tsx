import React, { createContext, useContext, useRef } from "react";

type MediaElement = HTMLAudioElement | HTMLVideoElement;

interface MediaPlayerContextType {
  registerPlayer: (id: string, player: MediaElement) => void;
  unregisterPlayer: (id: string) => void;
  playPlayer: (id: string) => void;
}

const MediaPlayerContext = createContext<MediaPlayerContextType | null>(null);

export function MediaPlayerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const playersRef = useRef<Map<string, MediaElement>>(new Map());

  const registerPlayer = (id: string, player: MediaElement) => {
    playersRef.current.set(id, player);
  };

  const unregisterPlayer = (id: string) => {
    playersRef.current.delete(id);
  };

  const playPlayer = (id: string) => {
    playersRef.current.forEach((player, playerId) => {
      if (playerId !== id && !player.paused) {
        player.pause();
      }
    });
  };

  return (
    <MediaPlayerContext.Provider
      value={{ registerPlayer, unregisterPlayer, playPlayer }}
    >
      {children}
    </MediaPlayerContext.Provider>
  );
}

export const useMediaPlayer = () => {
  const context = useContext(MediaPlayerContext);
  if (!context) {
    throw new Error("useMediaPlayer must be used within a MediaPlayerProvider");
  }
  return context;
};
