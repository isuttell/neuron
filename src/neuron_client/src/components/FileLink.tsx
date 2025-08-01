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
  className
}) => {
  // Determine the appropriate URL based on media type
  const linkUrl = (mediaType === "data" || mediaType === "code")
    ? `/code-viewer?url=${url}`
    : url;

  return (
    <a
      className={cn(
        "items-center gap-2 px-3 py-2 text-sm font-medium",
        "text-primary hover:text-primary/80",
        "bg-muted/50 hover:bg-muted rounded-md transition-colors",
        "min-w-0 max-w-full",
        className
      )}
      href={linkUrl}
      target="_blank"
      rel="noopener noreferrer"
    >
      <div className="truncate">{name}</div>
    </a>
  );
};

export default FileLink;
