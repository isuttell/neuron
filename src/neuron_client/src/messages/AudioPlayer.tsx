import React, { memo } from "react";

interface AudioPlayerProps {
  src: string;
  autoPlay?: boolean;
  preload?: string;
  loop?: boolean;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  preload = "auto",
  autoPlay = false,
  loop = false,
}) => {
  return (
    <audio
      controls
      autoPlay={autoPlay}
      loop={loop}
      preload={preload}
      className=""
    >
      <source src={src} type="audio/mpeg" />
      Your browser does not support the audio element.
    </audio>
  );
};

export default memo(AudioPlayer);
