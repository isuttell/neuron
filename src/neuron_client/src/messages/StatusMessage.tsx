import { cn } from "@/lib/utils";

const StatusMap = {
  error: "Error",
  idle: "Idle",
  streaming: "Streaming",
  thinking: "Thinking",
  tools: "Tools",
  update_memory: "Memory",
  update_title: "Title",
};

interface StatusMessageProps {
  status: string;
  className?: string;
  tagClassName?: string;
}

export function StatusMessage({
  status,
  className,
  tagClassName,
}: StatusMessageProps) {
  const tags = Array.from(
    new Set(
      status
        .split(",")
        .sort((a, b) => {
          if (a.trim() === "thinking") return -1;
          if (b.trim() === "thinking") return 1;
          if (a.trim() === "tools") return -1;
          if (b.trim() === "tools") return 1;
          return a.localeCompare(b);
        })
        .map((value) =>
          typeof StatusMap[value as keyof typeof StatusMap] === "string"
            ? StatusMap[value as keyof typeof StatusMap]
            : value.replace(/_/g, " ").replace(/tts/gi, "TTS").trim()
        )
    )
  );
  return (
    <div className={cn("flex flex-row", className)}>
      {tags.map((tag) => (
        <div key={tag} className={cn(tagClassName)}>
          {tag}
        </div>
      ))}
    </div>
  );
}
