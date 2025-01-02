import React, { memo } from "react";
import { cn } from "@/lib/utils";
interface AudioPlayerProps {
  className?: string;
  src: string;
  autoPlay?: boolean;
  preload?: string;
  loop?: boolean;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  className,
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
      className={cn("rounded-md", className)}
    >
      <source src={src} type="audio/mpeg" />
      Your browser does not support the audio element.
    </audio>
  );
};

export default memo(AudioPlayer);
