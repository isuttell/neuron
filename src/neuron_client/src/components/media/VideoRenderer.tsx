import { cn } from "@/lib/utils";
import { forwardRef } from "react";

interface VideoRendererProps {
  url: string;
  autoPlay?: boolean;
  controls?: boolean;
  loop?: boolean;
  muted?: boolean;
  preload?: "none" | "metadata" | "auto";
  poster?: string;
  duration?: number;
  className?: string;
  isThumbnail?: boolean;
}

export const VideoRenderer = forwardRef<HTMLVideoElement, VideoRendererProps>(
  (
    {
      url,
      autoPlay = false,
      controls = true,
      loop = false,
      muted = false,
      preload = "metadata",
      poster,
      duration,
      className,
      isThumbnail = false,
    },
    ref
  ) => {
    return (
      <div className={cn("relative", className)}>
        <video
          ref={ref}
          className={cn(
            "w-full h-full",
            isThumbnail && "rounded-lg cursor-pointer object-contain",
            !isThumbnail && "rounded-md object-contain"
          )}
          src={url}
          autoPlay={isThumbnail ? autoPlay : true}
          muted={isThumbnail ? true : muted}
          controls={isThumbnail ? controls : true}
          loop={isThumbnail ? loop : true}
          preload={preload}
          poster={poster}
          playsInline
        >
          <source src={url} type="video/mp4" />
        </video>
        {isThumbnail && duration && (
          <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
            {Math.floor(duration / 60)}:{(Math.floor(duration) % 60).toString().padStart(2, '0')}
          </div>
        )}
      </div>
    );
  }
);

VideoRenderer.displayName = "VideoRenderer";
