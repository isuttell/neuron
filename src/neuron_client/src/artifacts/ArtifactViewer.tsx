import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Content from "../messages/Content";
import { Message } from "../slices/messagesSlice";

interface Artifact {
  identifier: string;
  type: string;
  title: string;
  language: string;
  content: string;
  index: number;
}

export function extractAndReplaceArtifacts(messages: Message[]): {
  updatedMessages: Message[];
  artifacts: Record<string, Artifact[]>;
} {
  const artifactPattern =
    /:::artifact\{identifier="([^"]+)" type="([^"]+)" title="([^"]+)"\}\n```([\w-]+)?\n([\s\S]*?)(\n```\n:::|$)/g;
  const artifacts: Record<string, Artifact[]> = {};
  const updatedMessages = messages.map((message) => {
    let match;

    let updatedContent = Array.isArray(message.content)
      ? message.content.find((c) => c.type === "text")?.text
      : message.content;
    while (
      (match = artifactPattern.exec(
        Array.isArray(message.content)
          ? message.content.find((c) => c.type === "text")?.text || ""
          : message.content
      )) !== null
    ) {
      const [fullMatch, identifier, type, title, language, artifactContent] =
        match;
      if (!artifacts[identifier]) {
        artifacts[identifier] = [];
      }
      artifacts[identifier].push({
        index: artifacts[identifier].length,
        identifier,
        type,
        title,
        language,
        content: artifactContent,
      });
      updatedContent = updatedContent?.replace(fullMatch, "");
    }

    return { ...message, content: updatedContent || "" };
  });

  return { updatedMessages, artifacts };
}

const TypeMap = {
  "text/plain": "plain",
  "image/svg+xml": "svg",
  "text/html": "html",
};

export default function ArtifactViewer({
  artifacts,
}: {
  artifacts: Artifact[];
}) {
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(
    artifacts.length > 0 ? artifacts[artifacts.length - 1] : null
  );

  const handleSelectChange = (value: string) => {
    const artifact = artifacts.find(
      (artifact) => artifact.index === Number(value)
    );
    setSelectedArtifact(artifact || null);
  };

  useEffect(() => {
    setSelectedArtifact(
      artifacts.length > 0 ? artifacts[artifacts.length - 1] : null
    );
  }, [artifacts]);

  if (!selectedArtifact) {
    return null;
  }

  const type = selectedArtifact
    ? TypeMap[selectedArtifact?.type as keyof typeof TypeMap]
    : "plain";
  return (
    <div className="flex flex-col flex-1 border p-2 my-2 rounded-md">
      <h1 className="text-lg font-semibold mb-2">{selectedArtifact.title}</h1>
      <Select
        onValueChange={handleSelectChange}
        defaultValue={selectedArtifact.index.toString()}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select an version" />
        </SelectTrigger>
        <SelectContent>
          {artifacts.map((artifact) => (
            <SelectItem
              key={artifact.index.toString()}
              value={artifact.index.toString()}
            >
              #{(artifact.index + 1).toString()}
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
      </div>
    </div>
  );
}
