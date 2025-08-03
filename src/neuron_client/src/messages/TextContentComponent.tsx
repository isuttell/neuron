import React from "react";
import { FileText, ExternalLink, LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import TextDialog from "@/components/TextDialog";
import Content from "./Content";
import { cn } from "@/lib/utils";

interface TextContentProps {
  id: string;
  url: string;
  name: string;
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
  name,
  description,
  metadata,
  className,
  icon: IconComponent = FileText
}) => {
  const trigger = (
    <div
      className={cn(
        "group inline-flex items-center gap-2 px-3 py-2 text-sm font-medium",
        "text-primary hover:text-primary/80",
        "bg-muted/50 hover:bg-muted rounded-md transition-colors cursor-pointer",
        "min-w-0 max-w-[32%]",
        className
      )}
    >
      <IconComponent className="h-4 w-4 flex-shrink-0" />
      <span className="truncate">{name}</span>
      <ExternalLink className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
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
      title={name}
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
