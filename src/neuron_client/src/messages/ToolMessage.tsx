import React from "react";
import { Hammer } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import MediaArtifacts from "./MediaArtifacts";

interface ToolMessageProps {
  name?: string;
  textContent: string;
  artifact?: {
    type: string;
    media_type?: string;
    items?: Array<{
      id: string;
      url: string;
      caption: string;
      description?: string;
      duration?: number;
      metadata?: Record<string, unknown>;
    }>;
  };
  showTools: boolean;
  status?: string;
}

const ToolMessage: React.FC<ToolMessageProps> = ({
  name,
  textContent,
  artifact,
  showTools,
  status,
}) => {
  const hasMediaArtifact = artifact?.type === 'media';

  return (
    <div className="flex items-start space-x-2">
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <div className="w-10 h-10 mr-4 bg-primary rounded-full flex items-center justify-center min-w-[40px]">
            <Hammer className="text-primary-foreground" size={20} />
          </div>
        </TooltipTrigger>
        <TooltipContent side="right">
          {name || "Tool"}
        </TooltipContent>
      </Tooltip>

      <div className="flex flex-col flex-1">

        {/* For regular users: show only artifacts if present */}
        {!showTools && hasMediaArtifact ? (
          <MediaArtifacts
            artifact={artifact}
            preload={status === "streaming" ? "none" : "metadata"}
            className=""
          />
        ) : null}

        {/* For admins: show both content and artifacts */}
        {showTools && (
          <>
            {textContent && textContent.trim().length > 0 && (
              <div className="mb-4">
                <details className="group">
                  <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                    Tool Output
                  </summary>
                  <div className="mt-2 p-3 bg-zinc-900 rounded-md overflow-x-auto">
                    <pre className="text-xs whitespace-pre-wrap">{textContent}</pre>
                  </div>
                </details>
              </div>
            )}
            {hasMediaArtifact && (
              <MediaArtifacts
                artifact={artifact}
                preload={status === "streaming" ? "none" : "metadata"}
                className=""
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ToolMessage;
