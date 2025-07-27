import MediaDialogComponent from "@/components/MediaDialog";
import { ImageRenderer } from "@/components/media/ImageRenderer";
import { MediaActions } from "@/components/media/MediaActions";
import { cn } from "@/lib/utils";
import { MediaItem } from "@/types/media";

interface ImageContentProps {
  className?: string;
  url: string;
  alt?: string;
  caption?: string;
  description?: string;
  width?: number;
  height?: number;
  thumbnail_size?: "o" | "t" | "l" | "xl" | "xxl";
  display_size?: "o" | "t" | "l" | "xl" | "xxl";
  preload?: boolean;
  showControls?: boolean;
  mediaItem?: MediaItem;
  objectFit?: "cover" | "contain";
  metadata?: Record<string, unknown>;
}

const ImageContent: React.FC<ImageContentProps> = ({
  url,
  alt,
  description,
  width,
  height,
  className,
  thumbnail_size = "l",
  display_size = "o",
  preload = false,
  showControls = false,
  objectFit = "contain",
  mediaItem,
  metadata,
}) => {
  const trigger = (
    <div
      className={cn(
        "relative max-h-[400px] max-w-[500px] w-fit overflow-hidden",
        className
      )}
    >
      <ImageRenderer
        url={url}
        alt={alt}
        width={width}
        height={height}
        thumbnail_size={thumbnail_size}
        display_size={display_size}
        preload={preload}
        objectFit={objectFit}
        isThumbnail={true}
      />
      {showControls && (
        <div className="absolute bottom-2 right-2 space-x-2">
          <MediaActions
            url={url}
            mediaItem={mediaItem}
            variant="outline"
            copyLabel="Image URL"
            downloadFileName={url.split("/").pop() || "image"}
            className="flex gap-2"
          />
        </div>
      )}
    </div>
  );

  const content = (
    <ImageRenderer
      url={url}
      alt={alt}
      width={width}
      height={height}
      display_size={display_size}
      isThumbnail={false}
    />
  );

  const actions = (
    <MediaActions
      url={url}
      mediaItem={mediaItem}
      variant="ghost"
      size="icon"
      copyLabel="Image URL"
      downloadFileName={url.split("/").pop() || "image"}
      className="flex gap-2"
    />
  );

  return (
    <MediaDialogComponent
      trigger={trigger}
      title={alt || "Image Details"}
      actions={actions}
      metadata={metadata}
      description={description}
      dimensions={{ width, height }}
    >
      {content}
    </MediaDialogComponent>
  );
};

export default ImageContent;
