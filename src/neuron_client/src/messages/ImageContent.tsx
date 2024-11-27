import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogFooter,
  DialogClose,
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
          src={url}
          alt={alt}
          width={width}
          height={height}
        />
      </DialogTrigger>
      <DialogContent className="max-w-[95vw] max-h-[95vh] mx-auto box-border h-full flex-1 flex flex-col">
        <div
          className="w-full h-full bg-contain bg-no-repeat bg-center"
          style={{ backgroundImage: `url(${url})` }}
        ></div>
        <div className="text-sm border rounded-lg p-4 text-gray-300 whitespace-pre-line max-w-[1170px] mx-auto relative w-full h-full max-h-[130px]">
          <div className="p-4 absolute top-0 left-0 right-0 bottom-0 overflow-y-auto">
            {alt}
          </div>
        </div>
        <DialogFooter className="flex justify-end">
          <DialogClose>Close</DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ImageContent;
