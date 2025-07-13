import { MediaListDropdown } from "@/components/MediaListDropdown";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { MediaItem } from "@/types/media";
import { Copy, Download } from "lucide-react";
import { toast } from "sonner";

interface MediaActionsProps {
  url: string;
  mediaItem?: MediaItem;
  variant?: "outline" | "ghost";
  size?: "default" | "icon";
  className?: string;
  downloadFileName?: string;
  copyLabel?: string;
  downloadLabel?: string;
}

export const MediaActions: React.FC<MediaActionsProps> = ({
  url,
  mediaItem,
  variant = "ghost",
  size = "icon",
  className,
  downloadFileName,
  copyLabel = "Copy URL",
  downloadLabel = "Download",
}) => {
  const handleCopy = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    navigator.clipboard.writeText(url);
    toast(`${copyLabel} copied to clipboard`);
  };

  const handleDownload = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = downloadFileName || url.split("/").pop() || "media";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      toast(`${downloadLabel} completed`);
    } catch {
      toast.error("Download failed");
    }
  };

  return (
    <div className={className}>
      {mediaItem && (
        <MediaListDropdown
          variant={variant}
          size={size}
          mediaItemId={mediaItem.id}
        />
      )}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            onClick={handleCopy}
          >
            <Copy className={size === "icon" ? "w-4 h-4" : ""} />
            {size !== "icon" && <span className="sr-only">{copyLabel}</span>}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{copyLabel}</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size={size}
            onClick={handleDownload}
          >
            <Download className={size === "icon" ? "w-4 h-4" : ""} />
            {size !== "icon" && <span className="sr-only">{downloadLabel}</span>}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{downloadLabel}</TooltipContent>
      </Tooltip>
    </div>
  );
};
