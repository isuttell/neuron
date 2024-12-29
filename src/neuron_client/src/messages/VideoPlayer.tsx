import React, { memo } from "react";

interface VideoPlayerProps {
  className?: string;
  src: string;
  autoPlay?: boolean;
  preload?: string;
  loop?: boolean;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  className,
  src,
  preload = "auto",
  autoPlay = false,
  loop = false,
}) => {
  return (
    <video
      controls
      autoPlay={autoPlay}
      loop={loop}
      preload={preload}
      className={className}
    >
      <source src={src} type="video/mp4" />
      Your browser does not support the video element.
    </video>
  );
};

export default memo(VideoPlayer);
