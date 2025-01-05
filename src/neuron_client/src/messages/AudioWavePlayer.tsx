import React, { memo, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface AudioPlayerProps {
  className?: string;
  src: string;
  autoPlay?: boolean;
  preload?: string;
  loop?: boolean;
  children?: React.ReactNode;
  showWaveform?: boolean;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  className,
  src,
  preload = "auto",
  autoPlay = false,
  loop = false,
  children,
  showWaveform = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const waveformDataRef = useRef<number[]>([]);
  const isDraggingRef = useRef(false);

  // Load and analyze audio data
  useEffect(() => {
    if (!showWaveform) return;
    const loadAudioData = async () => {
      const width = canvasRef.current?.clientWidth || 512;

      try {
        // Fetch the audio file
        const response = await fetch(src);
        const arrayBuffer = await response.arrayBuffer();

        // Create audio context and decode the data
        const audioContext = new AudioContext();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // Get the raw audio data
        const channelData = audioBuffer.getChannelData(0); // Use first channel
        const points = width;
        const blockSize = Math.floor(channelData.length / points);

        // Process the data to get max values for each block
        const waveformData = [];
        for (let i = 0; i < points; i++) {
          const start = i * blockSize;
          const end = start + blockSize;
          let max = 0;

          // Find the maximum amplitude in this block
          for (let j = start; j < end; j++) {
            const amplitude = Math.abs(channelData[j]);
            if (amplitude > max) {
              max = amplitude;
            }
          }

          // Normalize to use full amplitude range
          const scaleFactor = 0.8; // Controls maximum height
          waveformData.push(max * scaleFactor);
        }

        waveformDataRef.current = waveformData;

        // Initial draw
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext("2d");
        if (canvas && ctx) {
          // Set canvas dimensions to match client size
          canvas.width = width;
          canvas.height = canvas.clientHeight;
          drawWaveform(ctx, canvas, 0);
        }

        // Cleanup
        audioContext.close();
      } catch (error) {
        console.error("Error loading audio data:", error);
        waveformDataRef.current = Array(width).fill(0.5);
      }
    };

    loadAudioData();
  }, [src, showWaveform]);

  // Handle resize
  useEffect(() => {
    if (!showWaveform) return;
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === canvas) {
          // Update canvas dimensions
          canvas.width = entry.contentRect.width;
          canvas.height = entry.contentRect.height;

          // Reload audio data with new width
          const loadAudioData = async () => {
            try {
              const response = await fetch(src);
              const arrayBuffer = await response.arrayBuffer();
              const audioContext = new AudioContext();
              const audioBuffer = await audioContext.decodeAudioData(
                arrayBuffer
              );
              const channelData = audioBuffer.getChannelData(0);

              const points = canvas.width;
              const blockSize = Math.floor(channelData.length / points);

              const waveformData = [];
              for (let i = 0; i < points; i++) {
                const start = i * blockSize;
                const end = start + blockSize;
                let max = 0;

                for (let j = start; j < end; j++) {
                  const amplitude = Math.abs(channelData[j]);
                  if (amplitude > max) {
                    max = amplitude;
                  }
                }

                const scaleFactor = 0.9;
                waveformData.push(max * scaleFactor);
              }

              waveformDataRef.current = waveformData;

              // Redraw with current progress
              const ctx = canvas.getContext("2d");
              const audio = audioRef.current;
              if (ctx && audio) {
                const currentProgress =
                  (audio.currentTime / audio.duration) * 100;
                drawWaveform(ctx, canvas, currentProgress);
              }

              audioContext.close();
            } catch (error) {
              console.error("Error reloading audio data:", error);
            }
          };

          loadAudioData();
          break;
        }
      }
    });

    resizeObserver.observe(canvas);

    return () => {
      resizeObserver.disconnect();
    };
  }, [src, showWaveform]);

  // Draw function that handles both initial render and updates
  const drawWaveform = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    currentProgress: number
  ) => {
    // Clear canvas
    ctx.fillStyle = "#111111";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const points = waveformDataRef.current.length;
    const sliceWidth = canvas.width / points;
    const centerY = canvas.height / 2;
    const progressPosition = Math.floor((currentProgress / 100) * points);

    // Draw center line
    ctx.beginPath();
    ctx.strokeStyle = "#333333";
    ctx.lineWidth = 1;
    ctx.moveTo(0, centerY);
    ctx.lineTo(canvas.width, centerY);
    ctx.stroke();

    // Draw waveform
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    // Draw played portion (blue)
    ctx.beginPath();
    ctx.strokeStyle = "rgb(6, 197, 255)";
    let x = 0;
    for (let i = 0; i < progressPosition; i++) {
      const amplitude = waveformDataRef.current[i];
      const barHeight = amplitude * (canvas.height / 2);
      ctx.moveTo(x, centerY + barHeight);
      ctx.lineTo(x, centerY - barHeight);
      x += sliceWidth;
    }
    ctx.stroke();

    // Draw unplayed portion (white)
    ctx.beginPath();
    ctx.strokeStyle = "#ffffff";
    for (let i = progressPosition; i < points; i++) {
      const amplitude = waveformDataRef.current[i];
      const barHeight = amplitude * (canvas.height / 2);
      ctx.moveTo(x, centerY + barHeight);
      ctx.lineTo(x, centerY - barHeight);
      x += sliceWidth;
    }
    ctx.stroke();
  };

  // Update progress
  useEffect(() => {
    if (!showWaveform) return;
    const audio = audioRef.current;
    if (!audio) return;

    let animationFrameId: number;

    const updateProgress = () => {
      const currentProgress = (audio.currentTime / audio.duration) * 100;

      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (canvas && ctx) {
        drawWaveform(ctx, canvas, currentProgress);
      }

      if (!audio.paused) {
        animationFrameId = requestAnimationFrame(updateProgress);
      }
    };

    // Start animation when playing
    const handlePlay = () => {
      updateProgress();
    };

    // Add this function
    const handlePause = () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };

    // Add this function
    const handleLoaded = () => {
      updateProgress();
    };

    // Update immediately when seeking or loading
    const handleTimeUpdate = () => {
      updateProgress();
    };

    // Handle seeking events from the native audio controls
    const handleSeeking = () => {
      const currentProgress = (audio.currentTime / audio.duration) * 100;
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (canvas && ctx) {
        drawWaveform(ctx, canvas, currentProgress);
      }
    };

    audio.addEventListener("play", handlePlay);
    audio.addEventListener("pause", handlePause);
    audio.addEventListener("ended", handlePause);
    audio.addEventListener("seeked", handleTimeUpdate);
    audio.addEventListener("seeking", handleSeeking); // Add seeking event
    audio.addEventListener("loadeddata", handleLoaded);
    audio.addEventListener("timeupdate", handleTimeUpdate);

    // Initial draw if audio is already loaded
    if (audio.readyState >= 2) {
      updateProgress();
    }

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      audio.removeEventListener("play", handlePlay);
      audio.removeEventListener("pause", handlePause);
      audio.removeEventListener("ended", handlePause);
      audio.removeEventListener("seeked", handleTimeUpdate);
      audio.removeEventListener("seeking", handleSeeking); // Remove seeking event
      audio.removeEventListener("loadeddata", handleLoaded);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
    };
  }, [showWaveform]);

  // Function to handle seeking based on mouse position
  const handleSeek = (e: React.MouseEvent<HTMLCanvasElement> | MouseEvent) => {
    const canvas = canvasRef.current;
    const audio = audioRef.current;
    if (!canvas || !audio) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));

    // Update audio time
    audio.currentTime = (percentage / 100) * audio.duration;

    // Force immediate waveform update
    const ctx = canvas.getContext("2d");
    if (ctx) {
      drawWaveform(ctx, canvas, percentage);
    }
  };

  // Add mouse event handlers
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
        e.preventDefault(); // Prevent text selection while dragging
        handleSeek(e);
      }
    };

    const handleMouseUp = () => {
      if (isDraggingRef.current) {
        isDraggingRef.current = false;
        const audio = audioRef.current;
        if (audio) {
          const currentProgress = (audio.currentTime / audio.duration) * 100;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            drawWaveform(ctx, canvas, currentProgress);
          }
        }
      }
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

  return (
    <div className="flex flex-col items-center w-full gap-2">
      {showWaveform && (
        <div className="relative w-full">
          <canvas
            ref={canvasRef}
            className="w-full h-[101px] rounded-md cursor-pointer"
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

export default memo(AudioPlayer);
