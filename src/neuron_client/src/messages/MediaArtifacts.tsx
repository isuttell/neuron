import React from "react";
import { getMediaContent, type AudioContent, type VideoContent, type ImageContent, type Content } from "@/slices/messagesSlice";
import StandaloneAudioContent from "./StandaloneAudioContent";
import VideoContentComponent from "./VideoContent";
import ImageContentComponent from "./ImageContent";

interface MediaArtifactsProps {
  content?: unknown[] | string;
  artifact?: {
    type: string;
    media_type?: string;
    items?: Array<{
      id: string;
      url: string;
      caption: string;
      description?: string;
      duration?: number;
      metadata?: Record<string, unknown>;
    }>;
  };
  preload?: "none" | "metadata" | "auto";
  className?: string;
}

const MediaArtifacts: React.FC<MediaArtifactsProps> = ({
  content,
  artifact,
  preload = "metadata",
  className = "mt-4"
}) => {
  // Handle artifact-based media (from tool messages)
  if (artifact?.type === "media" && artifact.items && artifact.items.length > 0) {
    return (
      <div className={`flex flex-col gap-4 ${className}`}>
        {artifact.items.map((item) => {
          switch (artifact.media_type) {
            case "audio":
              return (
                <StandaloneAudioContent
                  key={item.id}
                  url={item.url}
                  title={item.caption}
                  description={item.description}
                  preload={preload}
                  duration={item.duration}
                  metadata={item.metadata}
                  mediaItem={{
                    id: item.id,
                    url: item.url,
                    name: item.caption,
                    description: item.description || "",
                    media_type: "audio",
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    user_id: "",
                    thread_id: "",
                  }}
                />
              );

            case "video":
              return (
                <VideoContentComponent
                  key={item.id}
                  url={item.url}
                  caption={item.caption}
                  description={item.description}
                  duration={item.duration}
                  metadata={item.metadata}
                  preload={preload}
                />
              );

            case "image":
              return (
                <ImageContentComponent
                  key={item.id}
                  url={item.url}
                  alt={item.caption}
                  caption={item.caption}
                  description={item.description}
                  metadata={item.metadata}
                  thumbnail_size="xl"
                />
              );

            default:
              return null;
          }
        })}
      </div>
    );
  }

  // Handle content-based media (from AI messages)
  if (!content || typeof content === "string") {
    return null;
  }

  const mediaItems = getMediaContent(content as string | Content[]);

  if (mediaItems.length === 0) {
    return null;
  }

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {mediaItems.map((item) => {
        switch (item.type) {
          case "audio":
            return (
              <StandaloneAudioContent
                key={item.id}
                url={item.url}
                title={item.caption}
                description={(item as AudioContent).description || ""}
                preload={preload}
                duration={item.duration}
                metadata={item.metadata}
                mediaItem={{
                  id: item.id,
                  url: item.url,
                  name: item.caption,
                  description: (item as AudioContent).description || "",
                  media_type: "audio",
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                  user_id: "",
                  thread_id: "",
                }}
              />
            );

          case "video":
            return (
              <VideoContentComponent
                key={item.id}
                url={item.url}
                caption={item.caption}
                description={(item as VideoContent).description || ""}
                duration={item.duration}
                metadata={item.metadata}
                preload={preload}
              />
            );

          case "image":
            return (
              <ImageContentComponent
                key={item.id}
                url={item.url}
                alt={item.caption}
                caption={item.caption}
                description={(item as ImageContent).description || ""}
                metadata={item.metadata}
                thumbnail_size="xl"
              />
            );

          default:
            return null;
        }
      })}
    </div>
  );
};

export default MediaArtifacts;
