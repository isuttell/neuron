import React from "react";
import { FileText, ExternalLink, LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import TextDialog from "@/components/TextDialog";
import Content from "./Content";
import { cn } from "@/lib/utils";

interface TextContentProps {
  id: string;
  url: string;
  caption: string;
  description?: string;
  metadata?: {
    type?: string;
    query?: string;
    score?: number;
    [key: string]: unknown;
  };
  className?: string;
  icon?: LucideIcon;
}

const TextContentComponent: React.FC<TextContentProps> = ({
  url,
  caption,
  description,
  metadata,
  className,
  icon: IconComponent = FileText
}) => {
  const trigger = (
    <div className={cn("inline-block", className)}>
      <Badge
        variant="outline"
        className="group hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors cursor-pointer max-w-48"
      >
        <IconComponent className="h-3 w-3 mr-1 flex-shrink-0" />
        <span className="truncate">{caption}</span>
        <ExternalLink className="h-3 w-3 ml-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
      </Badge>
    </div>
  );

  const content = (
    <div className="p-6">
      {description && (
        <Content content={description} className="prose prose-sm lg:prose-base max-w-none" />
      )}
    </div>
  );

  const actions = (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => window.open(url, '_blank', 'noopener,noreferrer')}
      title="Open source link"
    >
      <ExternalLink className="h-4 w-4" />
    </Button>
  );

  return (
    <TextDialog
      trigger={trigger}
      title={caption}
      actions={actions}
      metadata={{
        ...metadata,
        url: url,
      }}
      icon={IconComponent}
    >
      {content}
    </TextDialog>
  );
};

export default TextContentComponent;
