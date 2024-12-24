import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

interface ImageContentProps {
  url: string;
  alt?: string;
  width?: number;
  height?: number;
}

const ImageContent: React.FC<ImageContentProps> = ({
  url,
  alt,
  width,
  height,
}) => {
  return (
    <Dialog>
      <DialogTrigger>
        <img
          className="w-full rounded-lg"
          src={url.replace(/\.(?=[^.]*$)/, "_t.")}
          alt={alt}
          width={width}
          height={height}
        />
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
