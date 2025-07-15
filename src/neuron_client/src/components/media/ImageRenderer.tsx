import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { useEffect, useRef, useState } from "react";

interface ImageRendererProps {
  url: string;
  alt?: string;
  width?: number;
  height?: number;
  thumbnail_size?: "o" | "t" | "l" | "xl" | "xxl";
  display_size?: "o" | "t" | "l" | "xl" | "xxl";
  preload?: boolean;
  objectFit?: "cover" | "contain";
  className?: string;
  isThumbnail?: boolean;
}

export const ImageRenderer: React.FC<ImageRendererProps> = ({
  url,
  alt,
  width,
  height,
  thumbnail_size = "l",
  display_size = "o",
  preload = false,
  objectFit = "cover",
  className,
  isThumbnail = false,
}) => {
  const [imageLoaded, setImageLoaded] = useState(!preload);
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false);
  const imageRef = useRef<HTMLImageElement>(null);

  const imageUrl = isThumbnail
    ? (url.endsWith(".gif") ? url : url.replace(/\.[^.]+$/, `_${thumbnail_size}.webp`))
    : (url.endsWith(".gif") ? url : url.replace(/\.[^.]+$/, `_${display_size}.webp`));

  useEffect(() => {
    if (preload && !isThumbnail) {
      const img = new Image();
      img.src = imageUrl;
      img.onload = () => {
        setImageLoaded(true);
      };
    }
  }, [imageUrl, preload, isThumbnail]);

  useEffect(() => {
    if (imageRef.current && isThumbnail) {
      imageRef.current.onload = () => {
        setThumbnailLoaded(true);
      };
    }
  }, [imageUrl, isThumbnail]);

  return (
    <div className={cn("relative", className)}>
      <img
        ref={imageRef}
        className={cn(
          "w-full h-full",
          isThumbnail && "rounded-lg cursor-pointer transition-opacity duration-500",
          isThumbnail && (thumbnailLoaded ? "opacity-100" : "opacity-50"),
          !isThumbnail && "max-w-full max-h-full object-contain",
          isThumbnail && (objectFit === "cover" ? "object-cover" : "object-contain")
        )}
        src={imageUrl}
        alt={alt}
        width={width}
        height={height}
        rel="noopener noreferrer"
      />
      {isThumbnail && !imageLoaded && (
        <Spinner className="absolute top-2 right-2 opacity-50" size={8} />
      )}
    </div>
  );
};
