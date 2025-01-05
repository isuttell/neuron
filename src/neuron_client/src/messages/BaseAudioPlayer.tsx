import React, { memo, useEffect, useRef, useState, useId } from "react";
import { cn } from "@/lib/utils";
import { useMediaPlayer } from "@/contexts/MediaPlayerContext";

interface BaseAudioPlayerProps {
  className?: string;
  src: string;
  autoPlay?: boolean;
  preload?: string;
  loop?: boolean;
  children?: React.ReactNode;
  showWaveform?: boolean;
  drawWaveform: (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    currentProgress: number,
    waveformData: number[]
  ) => void;
  processAudioData: (channelData: Float32Array, points: number) => number[];
  onEnded?: () => void;
  onPlay?: () => void;
  onPause?: () => void;
}

const BaseAudioPlayer: React.FC<BaseAudioPlayerProps> = ({
  className,
  src,
  preload = "auto",
  autoPlay = false,
  loop = false,
  children,
  showWaveform = true,
  drawWaveform,
  processAudioData,
  onEnded,
  onPlay,
  onPause,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const waveformDataRef = useRef<number[]>([]);
  const isDraggingRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const playerId = useId();
  const { registerPlayer, unregisterPlayer, playPlayer } = useMediaPlayer();

  const loadAudioData = async () => {
    if (!showWaveform) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      setIsLoading(true);
      const response = await fetch(src);
      const arrayBuffer = await response.arrayBuffer();
      const audioContext = new AudioContext();

      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const channelData = audioBuffer.getChannelData(0);
      const points = Math.floor(canvas.width);

      waveformDataRef.current = processAudioData(channelData, points);

      const ctx = canvas.getContext("2d");
      if (ctx) {
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        drawWaveform(ctx, canvas, progress, waveformDataRef.current);
      }

      await audioContext.close();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audio");
      console.error("Audio loading error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAudioData();
  }, [src, showWaveform]);

  const handleSeek = (e: React.MouseEvent<HTMLCanvasElement> | MouseEvent) => {
    const canvas = canvasRef.current;
    const audio = audioRef.current;
    if (!canvas || !audio) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    audio.currentTime = (percentage / 100) * audio.duration;

    // Update the progress state
    setProgress(percentage);
  };

  // Add a useEffect to redraw the waveform whenever progress changes
  useEffect(() => {
    if (
      showWaveform &&
      canvasRef.current &&
      waveformDataRef.current.length > 0
    ) {
      const ctx = canvasRef.current.getContext("2d");
      if (ctx) {
        drawWaveform(ctx, canvasRef.current, progress, waveformDataRef.current);
      }
    }
  }, [progress, drawWaveform, showWaveform]);

  useEffect(() => {
    if (!showWaveform) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleMouseDown = (e: MouseEvent) => {
      isDraggingRef.current = true;
      handleSeek(e);
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingRef.current) {
        handleSeek(e);
      }
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      canvas.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [showWaveform]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    let animationFrameId: number;

    const updateProgress = () => {
      if (!audio) return;

      const currentProgress = (audio.currentTime / audio.duration) * 100;
      setProgress(currentProgress);

      // Redraw waveform with current progress
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (ctx && canvas && waveformDataRef.current.length > 0) {
        drawWaveform(ctx, canvas, currentProgress, waveformDataRef.current);
      }

      // Continue animation loop only if audio is playing
      if (!audio.paused) {
        animationFrameId = requestAnimationFrame(updateProgress);
      }
    };

    const handlePlay = () => {
      animationFrameId = requestAnimationFrame(updateProgress);
    };

    const handlePause = () => {
      cancelAnimationFrame(animationFrameId);
    };

    const handleTimeUpdate = () => {
      const currentProgress = (audio.currentTime / audio.duration) * 100;
      setProgress(currentProgress);
    };

    // Listen for play/pause events
    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);

    audio.addEventListener("timeupdate", handleTimeUpdate);

    // Clean up
    return () => {
      cancelAnimationFrame(animationFrameId);
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
    };
  }, [drawWaveform]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    // Register this player
    registerPlayer(playerId, audio);

    // Add play event listener
    const handlePlay = () => {
      playPlayer(playerId);
      onPlay?.();
    };

    audio.addEventListener("play", handlePlay);

    // Cleanup
    return () => {
      unregisterPlayer(playerId);
      audio.removeEventListener("play", handlePlay);
    };
  }, [playerId, registerPlayer, unregisterPlayer, playPlayer]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => {
      onEnded?.();
    };

    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("ended", handleEnded);
    };
  }, [onEnded]);

  useEffect(() => {
    if (autoPlay && audioRef.current) {
      audioRef.current.play();
    }
  }, [autoPlay, audioRef.current]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handlePause = () => {
      onPause?.();
    };

    audio.addEventListener("pause", handlePause);

    return () => {
      audio.removeEventListener("pause", handlePause);
    };
  }, [onPause]);

  return (
    <div
      role="application"
      aria-label="Audio player"
      className="flex flex-col items-center w-full gap-2"
    >
      {error && <div className="text-red-500">{error}</div>}
      {isLoading && <div className="loading-spinner" />}
      {showWaveform && (
        <div
          className="relative w-full"
          role="slider"
          aria-label="Audio progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={audioRef.current?.currentTime ?? 0}
          tabIndex={0}
        >
          <canvas
            ref={canvasRef}
            className="w-full h-[100px] rounded-md cursor-pointer"
          />
        </div>
      )}
      <div className="w-full flex flex-row gap-2">
        <audio
          ref={audioRef}
          controls
          autoPlay={autoPlay}
          loop={loop}
          preload={preload}
          className={cn("rounded-md w-full", className)}
        >
          <source src={src} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
        {children}
      </div>
    </div>
  );
};

export default memo(BaseAudioPlayer);
