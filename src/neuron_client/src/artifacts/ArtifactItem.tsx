import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Content from "../messages/Content";
import { ArtifactVersion } from "./extractArtifacts";
import VideoPlayer from "../messages/VideoPlayer";
import AudioPlayer from "../messages/AudioPlayer";

const TypeMap = {
  "text/plain": "plain",
  "image/svg+xml": "svg",
  "text/html": "html",
  "video/mp4": "video",
  "audio/mp3": "audio",
  "image/*": "image",
  "image/png": "image",
  "image/jpeg": "image",
  "image/jpg": "image",
  "image/webp": "image",
};

export default function ArtifactItem({
  artifactVersions,
}: {
  artifactVersions: ArtifactVersion[];
}) {
  const [selectedIndex, setSelectedIndex] = useState<number>(
    artifactVersions.length > 0 ? artifactVersions.length - 1 : -1
  );

  const handleSelectChange = (value: string) => {
    setSelectedIndex(Number(value));
  };

  useEffect(() => {
    setSelectedIndex(
      artifactVersions.length > 0 ? artifactVersions.length - 1 : -1
    );
  }, [artifactVersions.length]);

  if (selectedIndex === -1 || !artifactVersions[selectedIndex]) {
    return null;
  }
  const selectedArtifact = artifactVersions[selectedIndex];
  const type =
    TypeMap[selectedArtifact.type as keyof typeof TypeMap] || "plain";

  return (
    <div className="flex flex-col flex-1 border p-2 my-2 rounded-md">
      <h1 className="text-lg font-semibold mb-2">{selectedArtifact.title}</h1>
      <Select
        onValueChange={handleSelectChange}
        defaultValue={selectedIndex.toString()}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select a version" />
        </SelectTrigger>
        <SelectContent>
          {artifactVersions.map((artifact, index) => (
            <SelectItem key={index.toString()} value={index.toString()}>
              #{(index + 1).toString()} {artifact.title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex flex-col flex-1 mt-2">
        {type === "plain" && (
          <Content
            content={`\`\`\`${selectedArtifact.language || ""}\n${
              selectedArtifact.content
            }`}
          />
        )}
        {type === "svg" && (
          <div
            className="flex-1 min-h-[200px]"
            dangerouslySetInnerHTML={{ __html: selectedArtifact.content }}
          />
        )}
        {type === "html" && (
          <iframe
            className="flex-1 min-h-[200px]"
            srcDoc={selectedArtifact.content}
          />
        )}
        {type === "image" && (
          <img
            className="rounded-md"
            src={selectedArtifact.content}
            alt={selectedArtifact.title}
          />
        )}
        {type === "video" && <VideoPlayer src={selectedArtifact.content} />}
        {type === "audio" && <AudioPlayer src={selectedArtifact.content} />}
      </div>
    </div>
  );
}
