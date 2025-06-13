import React from "react";
import { Bot } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import Content from "./Content";

interface SystemMessageProps {
  textContent: string;
  showTools: boolean;
  status?: string;
  onPromptClick?: (prompt: string) => void;
}

const SystemMessage: React.FC<SystemMessageProps> = ({
  textContent,
  showTools,
  status,
  onPromptClick,
}) => {
  let body = textContent;

  if (!showTools) {
    body = body.replace(/<\|AI\|>[\s\S]*?<\|AI\|>/g, "").trim();
  }

  return (
    <div className="flex items-start space-x-2">
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <div className="w-10 h-10 mr-4 bg-primary rounded-full flex items-center justify-center min-w-[40px]">
            <Bot className="text-primary-foreground" size={20} />
          </div>
        </TooltipTrigger>
        <TooltipContent side="right">System</TooltipContent>
      </Tooltip>

      <div className="flex flex-col flex-1">
        {body && body.trim().length > 0 && (
          !showTools ? (
            <Content
              content={body}
              preload={status === "streaming" ? "none" : "auto"}
              onPromptClick={onPromptClick}
            />
          ) : (
            <div className="whitespace-pre-wrap">{body}</div>
          )
        )}
      </div>
    </div>
  );
};

export default SystemMessage;
