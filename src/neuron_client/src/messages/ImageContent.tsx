import { useEffect, useState } from "react";
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
interface ImageContentProps {
  url: string;
  alt?: string;
  width?: number;
  height?: number;
  thumbnail_size?: "t" | "l" | "xl";
  preload?: boolean;
}

const ImageContent: React.FC<ImageContentProps> = ({
  url,
  alt,
  width,
  height,
  thumbnail_size = "t",
  preload = false,
}) => {
  const [imageLoaded, setImageLoaded] = useState(!preload);
  const { toast } = useToast();
  useEffect(() => {
    if (preload) {
      const img = new Image();
      img.src = url;
      img.onload = () => {
        setImageLoaded(true);
      };
    }
  }, [url]);
  return (
    <Dialog>
      <DialogTrigger asChild>
        <div className="relative">
          <img
            className="w-full rounded-lg border"
            src={
              url.endsWith(".gif")
                ? url
                : url.replace(/\.(?=[^.]*$)/, `_${thumbnail_size}.`)
            }
            alt={alt}
            width={width}
            height={height}
          />
          {!imageLoaded && <Spinner className="absolute top-2 right-2" />}
          <div className="absolute bottom-2 right-2 space-x-2">
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
                  asChild
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                >
                  <a
                    className="text-primary"
                    href={url}
                    download
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Download />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent>Download image</TooltipContent>
            </Tooltip>
          </div>
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>Image Details</DialogTitle>
          <DialogDescription>{alt}</DialogDescription>
        </DialogHeader>
        <div className="w-full overflow-hidden">
          <img
            src={url}
            alt={alt}
            className="w-full h-full rounded-lg bg-black object-contain"
          />
        </div>
        <Button className="w-full" variant="outline" asChild>
          <a
            className="text-primary"
            href={url}
            download
            target="_blank"
            rel="noopener noreferrer"
          >
            <Download className="w-4 h-4" />
            Download
          </a>
        </Button>
      </DialogContent>
    </Dialog>
  );
};

export default ImageContent;
