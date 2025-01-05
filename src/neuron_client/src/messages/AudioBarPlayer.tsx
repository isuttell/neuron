import React, { useRef, useEffect } from "react";
import BaseAudioPlayer from "./BaseAudioPlayer";
import type { AudioBarPlayerProps } from "./types";

const BAR_WIDTH = 2;
const GAP = 1;

const AudioBarPlayer: React.FC<AudioBarPlayerProps> = (props) => {
  const animationFrameRef = useRef<number>();
  const lastProgressRef = useRef<number>(0);
  const targetProgressRef = useRef<number>(0);

  const drawWaveform = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    currentProgress: number,
    waveformData: number[]
  ) => {
    // Update target progress
    targetProgressRef.current = currentProgress;

    // Start animation if not already running
    if (!animationFrameRef.current) {
      const animate = () => {
        const diff = targetProgressRef.current - lastProgressRef.current;
        if (Math.abs(diff) > 0.1) {
          // Smooth interpolation
          lastProgressRef.current += diff * 0.1;

          // Redraw with interpolated progress
          drawFrame(ctx, canvas, lastProgressRef.current, waveformData);
          animationFrameRef.current = requestAnimationFrame(animate);
        } else {
          // Reached target, stop animation
          lastProgressRef.current = targetProgressRef.current;
          drawFrame(ctx, canvas, lastProgressRef.current, waveformData);
          animationFrameRef.current = undefined;
        }
      };

      animationFrameRef.current = requestAnimationFrame(animate);
    }
  };

  // Separate drawing logic into its own function
  const drawFrame = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    progress: number,
    waveformData: number[]
  ) => {
    ctx.fillStyle = "#111111";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const centerY = canvas.height / 2;
    const barCount = Math.floor(canvas.width / (BAR_WIDTH + GAP));
    const progressPosition = Math.floor((progress / 100) * barCount);

    let x = 0;
    for (let i = 0; i < barCount; i++) {
      const amplitude = waveformData[i];
      const barHeight = Math.ceil(amplitude * (canvas.height / 2));

      const isPlayed = i <= progressPosition;
      ctx.fillStyle = isPlayed ? "rgb(6, 197, 255)" : "#ffffff";

      ctx.fillRect(x, centerY - barHeight, BAR_WIDTH, barHeight);
      ctx.fillRect(x, centerY, BAR_WIDTH, barHeight);

      x += BAR_WIDTH + GAP;
    }
  };

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const processAudioData = (channelData: Float32Array, points: number) => {
    const barCount = Math.floor(points / (BAR_WIDTH + GAP));
    const blockSize = Math.floor(channelData.length / barCount);
    const waveformData = [];

    for (let i = 0; i < barCount; i++) {
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
  };

  return (
    <BaseAudioPlayer
      {...props}
      drawWaveform={drawWaveform}
      processAudioData={processAudioData}
    />
  );
};

export default AudioBarPlayer;
