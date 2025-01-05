import React, { useRef } from "react";
import BaseAudioPlayer from "./BaseAudioPlayer";
import type { AudioBarPlayerProps } from "./types";

const BAR_WIDTH = 2;
const GAP = 1;

const AudioBarPlayer: React.FC<AudioBarPlayerProps> = (props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { currentProgress, waveformData } = props;

  const drawWaveform = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    currentProgress: number,
    waveformData: number[]
  ) => {
    ctx.fillStyle = "#111111";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const points = waveformData.length;
    const barWidth = BAR_WIDTH;
    const gap = GAP;
    const totalBarWidth = barWidth + gap;
    const centerY = canvas.height / 2;

    const totalWidth = totalBarWidth * points;
    const startX = (canvas.width - totalWidth) / 2;

    console.log("Current Progress:", currentProgress);
    console.log("Points:", points);

    const progressPosition = Math.floor(
      (Math.max(0, Math.min(currentProgress, 100)) / 100) * points
    );
    console.log("Progress Position:", progressPosition);

    let x = startX;
    for (let i = 0; i < points; i++) {
      const amplitude = waveformData[i];
      const barHeight = amplitude * (canvas.height / 2);

      const isPlayed = i < progressPosition;
      ctx.fillStyle = isPlayed ? "rgb(6, 197, 255)" : "#ffffff";

      // Combine the two fillRect calls into one
      ctx.fillRect(x, centerY - barHeight, barWidth, barHeight * 2);

      x += totalBarWidth;
    }
  };

  const processAudioData = (channelData: Float32Array, points: number) => {
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
  };

  return (
    <div>
      <canvas ref={canvasRef} width={512} height={100} />
      <BaseAudioPlayer
        {...props}
        drawWaveform={drawWaveform}
        processAudioData={processAudioData}
        currentProgress={currentProgress}
        waveformData={waveformData}
      />
    </div>
  );
};

export default AudioBarPlayer;
