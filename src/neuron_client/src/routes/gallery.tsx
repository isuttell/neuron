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
import { VirtuosoGrid } from "react-virtuoso";
import { forwardRef } from "react";
import type { GridComponents } from "react-virtuoso";
import TogglePlayerButton from "@/components/TogglePlayerButton";
import { Spinner } from "@/components/ui/spinner";
import { getImagesLoading } from "../slices/imagesSlice";
// Ensure that this stays out of the component,
// Otherwise the grid will remount with each render due to new component instances.
const gridComponents: GridComponents = {
  List: forwardRef(({ children, ...props }: any, ref) => (
    <div
      ref={ref}
      {...props}
      className="flex flex-wrap grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 lg:gap-4 xl:grid-cols-4 2xl:grid-cols-5"
    >
      {children}
    </div>
  )),
  Item: forwardRef(({ children, ...props }: any, ref) => (
    <div ref={ref} {...props} className="flex-none box-border">
      {children}
    </div>
  )),
};

export default function Gallery() {
  const images = useAppSelector(getImages);
  const loading = useAppSelector(getImagesLoading);
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(fetchImages());
  }, []);

  const sortedImages = [...images].sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1
  );

  if (loading && sortedImages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }

  return (
    <MediaPlayerProvider>
      <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
        <div className="flex justify-between mb-2 border-b pb-2">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-2xl font-bold">Recent Media</h1>
          <div className="flex-1" />
          <TogglePlayerButton />
        </div>
        <VirtuosoGrid
          totalCount={sortedImages.length}
          components={gridComponents}
          itemContent={(index) => {
            const image = sortedImages[index];
            return (
              <AspectRatio
                key={image.id}
                ratio={1}
                className="max-h-[1024px] max-w-[1024px] rounded-lg border border-gray-900 flex justify-center items-center p-1"
              >
                {image.media_type === "image" ? (
                  <ImageContent
                    key={image.id}
                    url={image.url}
                    alt={image.prompt ?? ""}
                    width={256}
                    height={256}
                    objectFit="contain"
                  />
                ) : null}
                {image.media_type === "video" ? (
                  <VideoContent key={image.id} url={image.url} />
                ) : null}
                {image.media_type === "audio" ? (
                  <AudioContent
                    className="w-full"
                    key={image.id}
                    url={image.url}
                    preload="metadata"
                  />
                ) : null}
              </AspectRatio>
            );
          }}
        />
      </div>
    </MediaPlayerProvider>
  );
}
