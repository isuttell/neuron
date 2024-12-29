import { Message } from "../slices/messagesSlice";
import { Artifact } from "./ArtifactItem";

export interface ArtifactVersion {
  identifier: string;
  type: string;
  title: string;
  language: string;
  content: string;
  index: number;
}

export interface Artifact {
  key: string;
  versions: ArtifactVersion[];
}

export function extractAndReplaceArtifacts(messages: Message[]): {
  updatedMessages: Message[];
  artifacts: Artifact[];
} {
  const artifactPattern =
    /:::artifact\{identifier="([^"]+)" type="([^"]+)" title="([^"]+)"\}(\n```)?([\w-]+)?\n([\s\S]*?)((\n```)?\n:::|$)/g;
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
      const [fullMatch, identifier, type, title, language, _, artifactContent] =
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

  return {
    updatedMessages,
    artifacts: Object.keys(artifacts).map((key) => ({
      key,
      versions: artifacts[key],
    })),
  };
}
