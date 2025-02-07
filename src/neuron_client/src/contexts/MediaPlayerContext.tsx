import React, { createContext, useRef } from "react";

export type MediaElement = HTMLAudioElement | HTMLVideoElement;

export interface MediaPlayerContextType {
  registerPlayer: (id: string, player: MediaElement) => void;
  unregisterPlayer: (id: string) => void;
  playPlayer: (id: string) => void;
}

export const MediaPlayerContext = createContext<MediaPlayerContextType | null>(
  null
);

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
