import React, { useEffect, useRef } from "react";

interface AudioWaveformProps {
  url: string;
  progress: number;
  className?: string;
}

export function AudioWaveform({
  url,
  progress,
  className,
}: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const waveformDataRef = useRef<number[]>([]);

  const processAudioData = (channelData: Float32Array, points: number) => {
    const blockSize = Math.floor(channelData.length / points);
    const waveform = [];

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
      waveform.push(max);
    }

    return waveform;
  };

  const drawWaveform = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    currentProgress: number,
    data: number[]
  ) => {
    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    const barWidth = width / data.length;
    const multiplier = height / 2;
    const progressWidth = (width * currentProgress) / 100;

    data.forEach((point, i) => {
      const x = i * barWidth;
      const barHeight = point * multiplier;

      // Draw played part
      if (x <= progressWidth) {
        ctx.fillStyle = "hsl(var(--primary))";
      } else {
        ctx.fillStyle = "hsl(var(--muted))";
      }

      ctx.fillRect(x, height / 2 - barHeight / 2, barWidth * 0.8, barHeight);
    });
  };

  useEffect(() => {
    const loadAudioData = async () => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      try {
        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        const audioContext = new AudioContext();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        const channelData = audioBuffer.getChannelData(0);

        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;

        const points = Math.floor(canvas.width / 2);
        waveformDataRef.current = processAudioData(channelData, points);

        const ctx = canvas.getContext("2d");
        if (ctx) {
          drawWaveform(ctx, canvas, progress, waveformDataRef.current);
        }

        await audioContext.close();
      } catch (err) {
        console.error("Audio loading error:", err);
      }
    };

    loadAudioData();
  }, [url]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || waveformDataRef.current.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (ctx) {
      drawWaveform(ctx, canvas, progress, waveformDataRef.current);
    }
  }, [progress]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ width: "100%", height: "40px" }}
    />
  );
}
