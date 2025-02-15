import { Button } from "@/components/ui/button";
import { Waveform } from "@/components/ui/waveform";
import { X } from "lucide-react";

interface AttachmentIndicatorProps {
  type: "file" | "audio";
  name?: string;
  onRemove: () => void;
}

export function AttachmentIndicator({
  type,
  name,
  onRemove,
}: AttachmentIndicatorProps) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-muted px-2 py-1 text-sm text-muted-foreground">
      {type === "audio" ? (
        <>
          <Waveform className="size-4" />
          <span>Audio recording attached</span>
        </>
      ) : (
        <>
          <span>File attached: {name}</span>
        </>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="h-4 w-4 p-0 hover:bg-transparent"
        onClick={onRemove}
      >
        <X className="size-3" aria-label="Remove attachment" />
      </Button>
    </div>
  );
}
