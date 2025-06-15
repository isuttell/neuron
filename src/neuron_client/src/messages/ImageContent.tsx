import { MediaListDropdown } from "@/components/MediaListDropdown";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { MediaItem } from "@/types/media";
import { Copy, Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";

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
  objectFit = "cover",
  mediaItem,
  metadata,
}) => {
  const [imageLoaded, setImageLoaded] = useState(!preload);
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false);
  const thumbnailRef = useRef<HTMLImageElement>(null);
  const thumbnailUrl = url.endsWith(".gif")
    ? url
    : url.replace(/\.[^.]+$/, `_${thumbnail_size}.webp`);

  const displayUrl = url.endsWith(".gif")
    ? url
    : url.replace(/\.[^.]+$/, `_${display_size}.webp`);
  useEffect(() => {
    if (preload) {
      const img = new Image();
      img.src = displayUrl;
      img.onload = () => {
        setImageLoaded(true);
      };
    }
  }, [displayUrl, preload]);

  useEffect(() => {
    if (thumbnailRef.current) {
      thumbnailRef.current.onload = () => {
        setThumbnailLoaded(true);
      };
    }
  }, [thumbnailUrl]);
  return (
    <Dialog>
      <DialogTrigger asChild>
        <div
          className={cn(
            "relative max-h-[400px] max-w-[500px] w-fit overflow-hidden",
            className
          )}
        >
          <img
            ref={thumbnailRef}
            className={cn(
              "rounded-lg w-full h-full cursor-pointer transition-opacity duration-500",
              thumbnailLoaded ? "opacity-100" : "opacity-50",
              objectFit === "cover" ? "object-cover" : "object-contain"
            )}
            src={thumbnailUrl}
            alt={alt}
            width={width}
            height={height}
            rel="noopener noreferrer"
          />
          {!imageLoaded && (
            <Spinner className="absolute top-2 right-2 opacity-50" size={8} />
          )}
          {showControls && (
            <div className="absolute bottom-2 right-2 space-x-2">
              {mediaItem && (
                <MediaListDropdown
                  variant="outline"
                  mediaItemId={mediaItem.id}
                />
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    className=""
                    variant="outline"
                    onClick={(e) => {
                      e.preventDefault();
                      navigator.clipboard.writeText(url);
                      toast("Image URL copied to clipboard");
                    }}
                  >
                    <Copy />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Copy image URL</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    className=""
                    variant="outline"
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const response = await fetch(url);
                        const blob = await response.blob();
                        const blobUrl = window.URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = blobUrl;
                        link.download = url.split("/").pop() || "image";
                        link.style.display = "none";
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        window.URL.revokeObjectURL(blobUrl);
                        toast("Image downloaded");
                      } catch {
                        toast.error("Download failed");
                      }
                    }}
                  >
                    <Download />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download</TooltipContent>
              </Tooltip>
            </div>
          )}
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] w-full h-[90vh] p-0 overflow-hidden">
        <div className="grid grid-cols-1 [@media(orientation:landscape)_and_(min-width:768px)]:grid-cols-[1fr,350px] [@media(min-width:1366px)]:grid-cols-[1fr,400px] h-full max-h-full overflow-y-auto">
          {/* Image Section */}
          <div className="relative flex items-center justify-center bg-black/5 dark:bg-white/5 min-h-0">
            <img
              src={displayUrl}
              alt={alt}
              className="max-w-full max-h-full object-contain"
            />
          </div>

          {/* Details Section */}
          <div className="flex flex-col border-t [@media(orientation:landscape)_and_(min-width:768px)]:border-t-0 [@media(orientation:landscape)_and_(min-width:768px)]:border-l [@media(min-width:1366px)]:border-t-0 [@media(min-width:1366px)]:border-l h-full min-h-0 [@media(orientation:landscape)_and_(min-width:768px)]:max-h-[90vh] [@media(min-width:1366px)]:max-h-[90vh]">
            <DialogHeader className="px-6 py-4 border-b shrink-0 text-left">
              <DialogTitle className="text-lg pr-8">{alt || "Image Details"}</DialogTitle>
            </DialogHeader>

            {/* Action Toolbar */}
            <div className="flex items-center gap-2 border-b px-6 py-2">
              {mediaItem && (
                <MediaListDropdown variant="ghost" size="icon" mediaItemId={mediaItem.id} />
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.preventDefault();
                      navigator.clipboard.writeText(url);
                      toast("Image URL copied to clipboard");
                    }}
                  >
                    <Copy className="w-4 h-4" />
                    <span className="sr-only">Copy URL</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Copy URL</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={async (e) => {
                      e.preventDefault();
                      try {
                        const response = await fetch(url);
                        const blob = await response.blob();
                        const blobUrl = window.URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = blobUrl;
                        link.download = url.split("/").pop() || "image";
                        link.style.display = "none";
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        window.URL.revokeObjectURL(blobUrl);
                        toast("Image downloaded");
                      } catch {
                        toast.error("Download failed");
                      }
                    }}
                  >
                    <Download className="w-4 h-4" />
                    <span className="sr-only">Download</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Download</TooltipContent>
              </Tooltip>
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="space-y-4 px-6 py-4">
                {description && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
                    <p className="text-sm whitespace-pre-wrap">{description}</p>
                  </div>
                )}

                {/* Image dimensions */}
                {(width || height) && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">Dimensions</h3>
                    <p className="text-sm">
                      {width && height ? `${width} × ${height}` : width ? `Width: ${width}` : `Height: ${height}`}
                    </p>
                  </div>
                )}

                {/* Metadata */}
                {metadata && Object.keys(metadata).length > 0 && (
                  <>
                    <div className="border-t -mx-6 my-4" />
                    <dl>
                      {Object.entries(metadata)
                        .filter(([, value]) => value !== null && value !== undefined && value !== '')
                        .map(([key, value]) => (
                          <div key={key} className="text-sm mb-4">
                            <dt className="font-medium text-muted-foreground capitalize mb-1">{key.replace(/_/g, ' ')}</dt>
                            <dd className="text-foreground break-words">{String(value)}</dd>
                          </div>
                        ))}
                    </dl>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ImageContent;
