import { useAppSelector } from "../hooks";
import { getImages } from "../slices/imagesSlice";
import { useEffect } from "react";
import { useAppDispatch } from "../hooks";
import { fetchImages } from "../actions/imageActions";
import ImageContent from "../messages/ImageContent";
import VideoContent from "../messages/VideoContent";
import AudioContent from "../messages/AudioContent";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
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
    <MediaPlayerProvider>
      <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
        <div className="flex justify-between mb-2 border-b pb-2">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-2xl font-bold">Gallery</h1>
          <div className="flex-1" />
        </div>
        <div className="overflow-y-auto grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-2 lg:gap-4">
          {sortedImages.map((image) => (
            <AspectRatio
              ratio={1}
              className="max-h-[1024px] max-w-[1024px] rounded-lg border border-gray-900"
            >
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
                <AudioContent
                  className="w-full p-2"
                  key={image.id}
                  url={image.url}
                  preload="metadata"
                />
              ) : null}
            </AspectRatio>
          ))}
        </div>
      </div>
    </MediaPlayerProvider>
  );
}
