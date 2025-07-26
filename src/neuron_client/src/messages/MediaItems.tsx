import React from "react";
import { MediaItem } from "@/types/media";
import AudioContentComponent from "./AudioContent";
import VideoContentComponent from "./VideoContent";
import ImageContentComponent from "./ImageContent";
import TextContentComponent from "./TextContentComponent";
import { Search } from "lucide-react";
import { FileLink } from "@/components/FileLink";

interface MediaItemsProps {
  mediaItems: MediaItem[];
  preload?: "none" | "metadata" | "auto";
  className?: string;
}

const MediaItems: React.FC<MediaItemsProps> = ({
  mediaItems,
  preload = "metadata",
  className = "mt-4"
}) => {
  if (!mediaItems || mediaItems.length === 0) {
    return null;
  }

  return (
    <div className={`flex flex-wrap gap-2 items-start ${className}`}>
      {mediaItems.map((item) => {
        switch (item.media_type) {
          case "audio":
            return (
              <AudioContentComponent
                key={item.id}
                url={item.url}
                title={item.name}
                description={item.description}
                mediaItem={item}
              />
            );

          case "video":
            return (
              <VideoContentComponent
                key={item.id}
                url={item.url}
                caption={item.name}
                description={item.description}
                preload={preload}
              />
            );

          case "image":
            return (
              <ImageContentComponent
                key={item.id}
                url={item.url}
                alt={item.name}
                caption={item.name}
                description={item.description}
                thumbnail_size="xl"
              />
            );

          case "search_result":
            return (
              <TextContentComponent
                key={item.id}
                id={item.id}
                url={item.url}
                caption={item.name}
                description={item.description}
                icon={Search}
              />
            );

          case "text":
            return (
              <TextContentComponent
                key={item.id}
                id={item.id}
                url={item.url}
                caption={item.name}
                description={item.description}
              />
            );

          case "html":
          case "data":
            return (
              <FileLink
                key={item.id}
                url={item.url}
                name={item.name}
                mediaType={item.media_type}
                description={item.description}
              />
            );

          default:
            return null;
        }
      })}
    </div>
  );
};

export default MediaItems;