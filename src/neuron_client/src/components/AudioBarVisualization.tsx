import { cn } from "@/lib/utils";
import { useRef, useEffect, useCallback } from "react";

interface AudioBarVisualizationProps {
  src: string;
  progress: number;
  className?: string;
  onSeek?: (progress: number) => void;
  backgroundColor?: string;
  barWidth?: number;
  gap?: number;
}

export function AudioBarVisualization({
  src,
  progress,
  className,
  onSeek,
  backgroundColor = "#111111",
  barWidth = 2,
  gap = 1,
}: AudioBarVisualizationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const waveformDataRef = useRef<number[]>([]);
  const rawChannelDataRef = useRef<Float32Array | null>(null);
  const isDraggingRef = useRef(false);
  const animationFrameRef = useRef<number>();
  const lastProgressRef = useRef<number>(0);
  const targetProgressRef = useRef<number>(0);

  const handleSeek = useCallback(
    (e: MouseEvent | React.MouseEvent) => {
      const canvas = canvasRef.current;
      if (!canvas || !onSeek) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = (x / rect.width) * 100;
      onSeek(Math.max(0, Math.min(100, percentage)));
    },
    [onSeek]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      isDraggingRef.current = true;
      handleSeek(e);
    },
    [handleSeek]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      handleSeek(e);
    },
    [handleSeek]
  );

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  useEffect(() => {
    if (onSeek) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);

      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [handleMouseMove, handleMouseUp, onSeek]);

  const updateCanvasDimensions = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const parent = canvas.parentElement;
    if (!parent) return;

    canvas.width = parent.clientWidth;
    canvas.height = canvas.clientHeight;
    const ctx = canvas.getContext("2d");

    canvas.style.width = `${parent.clientWidth}px`;
    canvas.style.height = `${canvas.clientHeight}px`;

    if (rawChannelDataRef.current) {
      waveformDataRef.current = processAudioData(rawChannelDataRef.current);
      if (ctx) {
        drawFrame(ctx, canvas, progress, waveformDataRef.current);
      }
    }

    if (waveformDataRef.current.length > 0) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        drawFrame(ctx, canvas, progress, waveformDataRef.current);
      }
    }
  }, [progress]);

  const processAudioData = useCallback(
    (channelData: Float32Array) => {
      const canvas = canvasRef.current;
      if (!canvas) return [];
      const points = Math.floor(canvas.clientWidth / (barWidth + gap));
      const blockSize = Math.floor(channelData.length / points);
      const waveformData: number[] = [];

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

      return waveformData;
    },
    [barWidth, gap]
  );

  const drawFrame = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    progress: number,
    waveformData: number[]
  ) => {
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const centerY = Math.round(canvas.height / 2);
    const barCount = waveformData.length;
    const progressPosition = Math.floor((progress / 100) * barCount);
    const totalWidth = (barWidth + gap) * barCount;
    const startX = (canvas.width - totalWidth) / 2;

    let x = startX;
    for (let i = 0; i < barCount; i++) {
      const amplitude = waveformData[i];
      const barHeight = Math.ceil(amplitude * (canvas.height / 2));

      const isPlayed = i <= progressPosition && progress > 0;
      ctx.fillStyle = isPlayed
        ? "rgb(6, 197, 255)"
        : "rgba(255, 255, 255, 0.86)";

      ctx.fillRect(x, centerY - barHeight, barWidth, barHeight);
      ctx.fillRect(x, centerY, barWidth, barHeight);

      x += barWidth + gap;
    }
  };

  useEffect(() => {
    const loadAudioData = async () => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      updateCanvasDimensions();
      const ctx = canvas.getContext("2d");

      try {
        const response = await fetch(src);
        const arrayBuffer = await response.arrayBuffer();
        const audioContext = new AudioContext();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        const channelData = audioBuffer.getChannelData(0);

        rawChannelDataRef.current = channelData;

        waveformDataRef.current = processAudioData(channelData);

        if (ctx) {
          drawFrame(ctx, canvas, progress, waveformDataRef.current);
        }

        await audioContext.close();
      } catch (err) {
        console.error("Audio loading error:", err);
      }
    };

    loadAudioData();
  }, [src]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || waveformDataRef.current.length === 0) return;

    targetProgressRef.current = progress;

    if (!animationFrameRef.current) {
      const animate = () => {
        const diff = targetProgressRef.current - lastProgressRef.current;
        if (Math.abs(diff) > 0.001) {
          lastProgressRef.current += diff * 0.25;

          const ctx = canvas.getContext("2d");
          if (ctx) {
            drawFrame(
              ctx,
              canvas,
              lastProgressRef.current,
              waveformDataRef.current
            );
          }
          animationFrameRef.current = requestAnimationFrame(animate);
        } else {
          lastProgressRef.current = targetProgressRef.current;
          const ctx = canvas.getContext("2d");
          if (ctx) {
            drawFrame(
              ctx,
              canvas,
              lastProgressRef.current,
              waveformDataRef.current
            );
          }
          animationFrameRef.current = undefined;
        }
      };

      animationFrameRef.current = requestAnimationFrame(animate);
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = undefined;
      }
    };
  }, [progress]);

  useEffect(() => {
    if (!canvasRef.current) return;
    const handleResize = () => {
      updateCanvasDimensions();
    };

    const observer = new ResizeObserver(handleResize);
    observer.observe(canvasRef.current.parentElement || canvasRef.current);

    window.addEventListener("resize", handleResize);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", handleResize);
    };
  }, [updateCanvasDimensions]);

  return (
    <canvas
      ref={canvasRef}
      className={cn("w-full h-full", className)}
      onMouseDown={onSeek ? handleMouseDown : undefined}
      style={{
        backgroundColor,
        cursor: onSeek ? "pointer" : "default",
      }}
    />
  );
}
