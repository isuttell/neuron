import { useEffect, useState, useRef } from "react";
import { Download, Copy } from "lucide-react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { MediaListDropdown } from "@/components/MediaListDropdown";
import { MediaItem } from "@/slices/mediaSlice";

interface ImageContentProps {
  className?: string;
  url: string;
  alt?: string;
  width?: number;
  height?: number;
  thumbnail_size?: "o" | "t" | "l" | "xl" | "xxl";
  display_size?: "o" | "t" | "l" | "xl" | "xxl";
  preload?: boolean;
  showControls?: boolean;
  mediaItem?: MediaItem;
  objectFit?: "cover" | "contain";
}

const ImageContent: React.FC<ImageContentProps> = ({
  url,
  alt,
  width,
  height,
  className,
  thumbnail_size = "l",
  display_size = "o",
  preload = false,
  showControls = false,
  objectFit = "cover",
  mediaItem,
}) => {
  const [imageLoaded, setImageLoaded] = useState(!preload);
  const [thumbnailLoaded, setThumbnailLoaded] = useState(false);
  const { toast } = useToast();
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
            "relative max-h-[1024px] max-w-[1024px] w-full h-full overflow-hidden",
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
                      toast({
                        title: "Image URL copied to clipboard",
                      });
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
                        toast({
                          title: "Image downloaded",
                        });
                      } catch {
                        toast({
                          title: "Download failed",
                          variant: "destructive",
                        });
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
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>Image Details</DialogTitle>
          {alt && <DialogDescription>{alt}</DialogDescription>}
        </DialogHeader>
        <div className="w-full overflow-hidden">
          <img
            src={displayUrl}
            alt={alt}
            className="w-full h-full object-contain"
          />
        </div>
        <div className="flex justify-end gap-2">
          {mediaItem && (
            <MediaListDropdown variant="outline" mediaItemId={mediaItem.id} />
          )}
          <Button
            className=""
            variant="outline"
            onClick={(e) => {
              e.preventDefault();
              navigator.clipboard.writeText(url);
              toast({
                title: "Image URL copied to clipboard",
              });
            }}
          >
            <Copy className="w-4 h-4" />
            <span className="sr-only">Copy</span>
          </Button>
          <Button
            variant="outline"
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
                toast({
                  title: "Image downloaded",
                });
              } catch {
                toast({
                  title: "Download failed",
                  variant: "destructive",
                });
              }
            }}
          >
            <Download className="w-4 h-4" />
            <span className="sr-only">Download</span>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ImageContent;
