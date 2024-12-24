import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogFooter,
  DialogClose,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ImageModel } from "../slices/imagesSlice";
import Loading from "../lib/loading";
interface ImageCardProps {
  image: ImageModel;
}

const ImageCard: React.FC<ImageCardProps> = ({ image }) => {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="flex w-full h-full items-center justify-center bg-secondary rounded-lg">
        {image.image ? (
          <img
            className="w-full h-auto object-cover rounded-lg"
            src={image.image.replace(/\.(?=[^.]*$)/, "_t.")}
            alt={image.prompt.slice(0, 256)}
          />
        ) : (
          <Loading />
        )}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader className="mb-4">
          <DialogTitle>Image Viewer</DialogTitle>
        </DialogHeader>
        <div className="flex-1">
          {image.image ? (
            <img
              className="w-full h-auto object-cover"
              src={image.image}
              alt={image.prompt.slice(0, 256)}
            />
          ) : (
            <Loading />
          )}
        </div>
        <div className="text-center text-sm text-gray-500 my-2">
          {image.prompt.slice(0, 256)}
        </div>

        <DialogFooter className="flex justify-end">
          <DialogClose asChild>
            <Button type="button" variant="ghost">
              Close
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ImageCard;
