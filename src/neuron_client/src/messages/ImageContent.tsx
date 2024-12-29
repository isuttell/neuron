import { useEffect, useState } from "react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
interface ImageContentProps {
  url: string;
  alt?: string;
  width?: number;
  height?: number;
  thumbnail_size?: "t" | "l" | "xl";
}

const ImageContent: React.FC<ImageContentProps> = ({
  url,
  alt,
  width,
  height,
  thumbnail_size = "t",
}) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  useEffect(() => {
    const img = new Image();
    img.src = url;
    img.onload = () => {
      setImageLoaded(true);
    };
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
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <DialogHeader>
          <DialogTitle>Image Details</DialogTitle>
          <DialogDescription>{alt}</DialogDescription>
        </DialogHeader>
        <div
          className="w-full h-full bg-contain bg-no-repeat bg-center"
          style={{ backgroundImage: `url(${url})` }}
        ></div>
      </DialogContent>
    </Dialog>
  );
};

export default ImageContent;
