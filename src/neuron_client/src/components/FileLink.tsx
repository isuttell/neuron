import React from "react";
import { cn } from "@/lib/utils";

interface FileLinkProps {
  url: string;
  name: string;
  mediaType: string;
  description?: string;
  className?: string;
}

/**
 * Renders a file link with appropriate URL handling based on media type.
 * Code and data files are redirected to the code viewer.
 */
export const FileLink: React.FC<FileLinkProps> = ({
  url,
  name,
  mediaType,
  description,
  className
}) => {
  // Determine the appropriate URL based on media type
  const linkUrl = (mediaType === "data" || mediaType === "code")
    ? `/code-viewer?url=${url}`
    : url;

  return (
    <a
      className={cn(
        "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium",
        "text-primary hover:text-primary/80",
        "bg-muted/50 hover:bg-muted rounded-md transition-colors",
        className
      )}
      href={linkUrl}
      target="_blank"
      rel="noopener noreferrer"
    >
      <span className="truncate max-w-sm">{name}</span>
      {description && (
        <span className="text-xs text-muted-foreground">({description})</span>
      )}
    </a>
  );
};

export default FileLink;
