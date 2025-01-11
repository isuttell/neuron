import React, {
  createContext,
  useContext,
  useRef,
  useState,
  useEffect,
  useCallback,
} from "react";

interface QueueItem {
  url: string;
  title?: string;
  key: string;
}

interface GlobalAudioContextType {
  currentUrl: string | null;
  playAudio: (url: string, title?: string, playNow?: boolean) => void;
  toggleAudio: () => void;
  isPlaying: boolean;
  isLoading: boolean;
  error: string | null;
  progress: number;
  queue: QueueItem[];
  skipNext: () => void;
  skipPrevious: () => void;
  clearQueue: () => void;
  currentTime: string;
  duration: string;
  seek: (percentage: number) => void;
  autoAdvance: boolean;
  toggleAutoAdvance: () => void;
  addToQueue: (url: string, title?: string) => void;
}

const GlobalAudioContext = createContext<GlobalAudioContextType | undefined>(
  undefined
);

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

export function GlobalAudioProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [currentUrl, setCurrentUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [currentTime, setCurrentTime] = useState("0:00");
  const [duration, setDuration] = useState("0:00");
  const [hasEnded, setHasEnded] = useState(false);
  const [autoAdvance, setAutoAdvance] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(new Audio());
  const queueIndexRef = useRef<number>(0);

  const loadAndPlay = useCallback(
    (queueToPlay: QueueItem[], index: number = 0) => {
      if (!audioRef.current || queueToPlay.length === 0) return;
      const currentItem = queueToPlay[index];
      if (!currentItem) return;

      if (currentItem.url !== currentUrl) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        setIsLoading(true);
        setError(null);
        setCurrentUrl(currentItem.url);
        audioRef.current.src = currentItem.url;
        audioRef.current.preload = "auto";
      }
      const playPromise = audioRef.current.play();
      if (playPromise) {
        playPromise
          .then(() => {
            setIsLoading(false);
          })
          .catch((err) => {
            console.error("Failed to play audio:", err);
            setError("Audio playback requires user interaction");
            setIsLoading(false);
          });
      }
    },
    [currentUrl]
  );

  const startQueue = useCallback(() => {
    if (queue.length === 0) return;
    loadAndPlay(queue, queueIndexRef.current);
  }, [queue, loadAndPlay]);

  const addToQueue = useCallback((url: string, title?: string) => {
    setQueue((prev) => {
      const itemIndex = prev.findIndex((item) => item.url === url);
      if (itemIndex >= 0) return prev; // Already in queue

      const newItem = {
        url,
        title,
        key: Math.random().toString(36).substring(2),
      };
      return [...prev, newItem];
    });
  }, []);

  const playAudio = useCallback(
    (url: string, title?: string, playNow: boolean = true) => {
      if (!audioRef.current) return;

      if (playNow && isPlaying) {
        audioRef.current.pause();
      }

      const itemIndex = queue.findIndex((item) => item.url === url);
      if (itemIndex >= 0) {
        if (playNow) {
          queueIndexRef.current = itemIndex;
          loadAndPlay(queue, queueIndexRef.current);
        }
        return;
      }

      const newItem = {
        url,
        title,
        key: Math.random().toString(36).substring(2),
      };
      const newQueue = playNow ? [newItem, ...queue] : [...queue, newItem];
      setQueue(newQueue);

      if (playNow) {
        queueIndexRef.current = 0;
        loadAndPlay(newQueue, 0);
      }
    },
    [isPlaying, queue, loadAndPlay]
  );

  const toggleAudio = useCallback(() => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((err) => {
        setError(err.message);
      });
    }
  }, [isPlaying]);

  const skipNext = useCallback(() => {
    if (queue.length === 0) return;

    if (queueIndexRef.current >= queue.length - 1) return;

    const nextIndex = queueIndexRef.current + 1;
    queueIndexRef.current = nextIndex;
    startQueue();
  }, [queue, startQueue]);

  const skipPrevious = useCallback(() => {
    if (queue.length === 0) return;

    if (queueIndexRef.current <= 0) return;

    const prevIndex = queueIndexRef.current - 1;
    queueIndexRef.current = prevIndex;
    startQueue();
  }, [queue, startQueue]);

  const clearQueue = useCallback(() => {
    setQueue([]);
    queueIndexRef.current = 0;
    if (audioRef.current) {
      audioRef.current.pause();
      setCurrentUrl(null);
    }
  }, []);

  const seek = useCallback((percentage: number) => {
    if (!audioRef.current) return;
    const time = (percentage / 100) * audioRef.current.duration;
    audioRef.current.currentTime = time;
    setProgress(percentage);
  }, []);

  const toggleAutoAdvance = useCallback(() => {
    setAutoAdvance((prev) => !prev);
  }, []);

  const handleTimeUpdate = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const newProgress = (audio.currentTime / audio.duration) * 100;
    const newCurrentTime = formatTime(audio.currentTime);

    if (Math.abs(newProgress - progress) > 0.1) {
      setProgress(newProgress);
    }

    if (newCurrentTime !== currentTime) {
      setCurrentTime(newCurrentTime);
    }
  }, [progress, currentTime]);

  useEffect(() => {
    const audio = audioRef.current;

    const handleLoadStart = () => {
      setIsLoading(true);
      setError(null);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
    };

    const handleError = () => {
      setIsLoading(false);
      setError("Failed to load audio");
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setHasEnded(true);
      setProgress(0);
      audioRef.current!.currentTime = 0;
    };

    const handlePause = () => {
      setIsPlaying(false);
    };

    const handlePlay = () => {
      setIsPlaying(true);
    };

    const handleLoadedMetadata = () => {
      if (audio) {
        setDuration(formatTime(audio.duration));
      }
    };

    audio.addEventListener("loadstart", handleLoadStart);
    audio.addEventListener("canplay", handleCanPlay);
    audio.addEventListener("error", handleError);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);

    return () => {
      audio.removeEventListener("loadstart", handleLoadStart);
      audio.removeEventListener("canplay", handleCanPlay);
      audio.removeEventListener("error", handleError);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
    };
  }, [handleTimeUpdate]);

  useEffect(() => {
    if (autoAdvance && hasEnded && queueIndexRef.current < queue.length - 1) {
      queueIndexRef.current++;
      startQueue();
      setHasEnded(false);
    }
  }, [hasEnded, queue, startQueue, autoAdvance]);

  return (
    <GlobalAudioContext.Provider
      value={{
        currentUrl,
        playAudio,
        toggleAudio,
        isPlaying,
        isLoading,
        error,
        progress,
        queue,
        skipNext,
        skipPrevious,
        clearQueue,
        currentTime,
        duration,
        seek,
        autoAdvance,
        toggleAutoAdvance,
        addToQueue,
      }}
    >
      {children}
    </GlobalAudioContext.Provider>
  );
}

export const useGlobalAudio = () => {
  const context = useContext(GlobalAudioContext);
  if (!context) {
    throw new Error("useGlobalAudio must be used within a GlobalAudioProvider");
  }
  return context;
};
