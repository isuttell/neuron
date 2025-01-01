import { useAppSelector } from "../hooks";
import { getImages } from "../slices/imagesSlice";
import { useEffect } from "react";
import { useAppDispatch } from "../hooks";
import { fetchImages } from "../actions/imageActions";
import ImageContent from "../messages/ImageContent";
import VideoContent from "../messages/VideoContent";
import AudioPlayer from "../messages/AudioPlayer";
import { AspectRatio } from "@/components/ui/aspect-ratio";
export default function Gallery() {
  const images = useAppSelector(getImages);
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(fetchImages());
  }, []);

  const sortedImages = [...images].sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1
  );
  return (
    <div className="flex flex-1 p-4 pl-0 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">Gallery</h1>
      </div>
      <div className="overflow-y-auto grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {sortedImages.map((image) => (
          <div className="max-h-[1024px] max-w-[1024px]">
            {image.media_type === "image" ? (
              <ImageContent
                key={image.id}
                url={image.url}
                alt={image.prompt ?? ""}
                width={256}
                height={256}
              />
            ) : null}
            {image.media_type === "video" ? (
              <VideoContent key={image.id} url={image.url} />
            ) : null}
            {image.media_type === "audio" ? (
              <AudioPlayer className="w-full" key={image.id} src={image.url} />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
