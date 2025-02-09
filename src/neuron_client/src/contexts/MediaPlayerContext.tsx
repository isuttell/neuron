import React, { createContext, useRef } from "react";

export type MediaElement = HTMLAudioElement | HTMLVideoElement;

export interface MediaPlayerContextType {
  registerPlayer: (id: string, url: string, player: MediaElement) => void;
  unregisterPlayer: (id: string, url: string) => void;
  playPlayer: (id: string) => void;
  getOrCreateAudio: (url: string) => HTMLAudioElement;
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
  const audioCache = useRef<Map<string, HTMLAudioElement>>(new Map());

  const getOrCreateAudio = (url: string) => {
    if (!audioCache.current.has(url)) {
      const audio = new Audio();
      audio.src = url;
      audioCache.current.set(url, audio);
    }
    return audioCache.current.get(url)!;
  };

  const registerPlayer = (id: string, url: string, player: MediaElement) => {
    if (!audioCache.current.has(url)) {
      audioCache.current.set(url, player as HTMLAudioElement);
    }
    playersRef.current.set(id, audioCache.current.get(url)!);
  };

  const unregisterPlayer = (id: string, url: string) => {
    playersRef.current.delete(id);
    // Only remove from cache if no other players are using this URL
    if (!Array.from(playersRef.current.values()).some((p) => p.src === url)) {
      const audio = audioCache.current.get(url);
      if (audio) {
        audio.pause();
        audioCache.current.delete(url);
      }
    }
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
      value={{ registerPlayer, unregisterPlayer, playPlayer, getOrCreateAudio }}
    >
      {children}
    </MediaPlayerContext.Provider>
  );
}
