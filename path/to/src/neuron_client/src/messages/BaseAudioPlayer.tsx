import React, { useEffect, useRef, useState } from "react";
import AudioBarPlayer from "./AudioBarPlayer";

const BaseAudioPlayer: React.FC = (props) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [waveformData, setWaveformData] = useState<number[]>([]);

  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement) return;

    const updateProgress = () => {
      if (audioElement.duration) {
        const progress =
          (audioElement.currentTime / audioElement.duration) * 100;
        console.log("Updating Progress:", progress);
        setCurrentProgress(progress);
      }
    };

    audioElement.addEventListener("timeupdate", updateProgress);

    return () => {
      audioElement.removeEventListener("timeupdate", updateProgress);
    };
  }, []);

  useEffect(() => {
    const audioElement = audioRef.current;
    if (!audioElement) return;

    const handleLoadedData = () => {
      const channelData =
        audioElement.audioBuffer?.getChannelData(0) || new Float32Array();
      const processedData = props.processAudioData(channelData, 600); // Assuming 600 points
      setWaveformData(processedData);
    };

    audioElement.addEventListener("loadeddata", handleLoadedData);

    return () => {
      audioElement.removeEventListener("loadeddata", handleLoadedData);
    };
  }, [props.processAudioData]);

  useEffect(() => {
    console.log("Waveform Data Updated:", waveformData);
  }, [waveformData]);

  return (
    <AudioBarPlayer
      {...props}
      currentProgress={currentProgress}
      waveformData={waveformData}
    />
  );
};

export default BaseAudioPlayer;
