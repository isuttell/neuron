import { useAppSelector } from "../hooks";
import { useEffect, useRef } from "react";
import { useAppDispatch } from "../hooks";
import {
  fetchRecentMedia,
  selectAllMedia,
  selectMediaLoading,
} from "../slices/mediaSlice";
import ImageContent from "../messages/ImageContent";
import VideoContent from "../messages/VideoContent";
import AudioContent from "../messages/AudioContent";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { MediaPlayerProvider } from "@/contexts/MediaPlayerContext";
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { VirtuosoGrid } from "react-virtuoso";
import { forwardRef } from "react";
import type { GridComponents } from "react-virtuoso";
import { Spinner } from "@/components/ui/spinner";
import type { HTMLAttributes } from "react";

// Ensure that this stays out of the component,
// Otherwise the grid will remount with each render due to new component instances.
const gridComponents: GridComponents = {
  List: forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ children, ...props }, ref) => (
      <div
        ref={ref}
        {...props}
        className="flex flex-wrap grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 lg:gap-4 xl:grid-cols-4 2xl:grid-cols-5"
      >
        {children}
      </div>
    )
  ),
  Item: forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
    ({ children, ...props }, ref) => (
      <div ref={ref} {...props} className="flex-none box-border">
        {children}
      </div>
    )
  ),
};

interface RecentMediaProps {
  limit?: number;
}

export default function RecentMedia({ limit = 16 }: RecentMediaProps) {
  const mediaItems = useAppSelector(selectAllMedia);
  const loading = useAppSelector(selectMediaLoading);
  const dispatch = useAppDispatch();
  const offset = useRef(0);

  useEffect(() => {
    dispatch(fetchRecentMedia({ offset: offset.current, limit }));
  }, [dispatch, limit]);

  if (loading && mediaItems.length === 0) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }
  const sortedMediaItems = mediaItems
    .slice()
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  return (
    <MediaPlayerProvider>
      <div className="flex flex-1 p-4 ipad-top-spacing mobile-safe-top flex-col flex-nowrap max-h-screen overflow-auto">
        <div className="flex justify-between mb-2 border-b pb-2">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-2xl font-bold">Recent Media</h1>
          <div className="flex-1" />
        </div>
        <VirtuosoGrid
          totalCount={sortedMediaItems.length}
          components={gridComponents}
          data={sortedMediaItems}
          endReached={() => {
            offset.current += limit;
            dispatch(fetchRecentMedia({ offset: offset.current, limit }));
          }}
          itemContent={(_, mediaItem) => {
            return (
              <AspectRatio
                key={mediaItem.id}
                ratio={1}
                className="max-h-[1024px] max-w-[1024px] rounded-lg border border-gray-900 flex justify-center items-center p-1"
              >
                {mediaItem.media_type === "image" ? (
                  <ImageContent
                    key={mediaItem.id}
                    url={mediaItem.url}
                    alt={mediaItem.name}
                    description={mediaItem.description}
                    width={256}
                    height={256}
                    objectFit="cover"
                    mediaItem={mediaItem}
                    showControls={true}
                  />
                ) : null}
                {mediaItem.media_type === "video" ? (
                  <VideoContent
                    key={mediaItem.id}
                    url={mediaItem.url}
                    mediaItem={mediaItem}
                    showControls={true}
                  />
                ) : null}
                {mediaItem.media_type === "audio" ? (
                  <AudioContent
                    className="w-full"
                    key={mediaItem.id}
                    url={mediaItem.url}
                    title={mediaItem.name}
                    description={mediaItem.description}
                    mediaItem={mediaItem}
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
