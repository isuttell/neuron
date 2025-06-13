import React from "react";
import { User } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import Content from "./Content";
import MediaArtifacts from "./MediaArtifacts";

interface HumanMessageProps {
  textContent: string;
  content?: unknown[] | string;
  showTools: boolean;
  status?: string;
  onPromptClick?: (prompt: string) => void;
  user?: {
    picture?: string | null;
    nickname?: string | null;
  };
}

const HumanMessage: React.FC<HumanMessageProps> = ({
  textContent,
  content,
  showTools,
  status,
  onPromptClick,
  user,
}) => {
  let body = textContent;

  if (!showTools) {
    body = body.replace(/<\|AI\|>[\s\S]*?<\|AI\|>/g, "").trim();
  }

  return (
    <div className="flex items-start space-x-2">
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <div className="w-10 h-10 mr-4 bg-muted rounded-full flex items-center justify-center min-w-[40px]">
            <Avatar>
              <AvatarImage src={user?.picture || ""} />
              <AvatarFallback>
                <User className="text-muted-foreground" size={20} />
              </AvatarFallback>
            </Avatar>
          </div>
        </TooltipTrigger>
        <TooltipContent side="right">
          {user?.nickname || "Human"}
        </TooltipContent>
      </Tooltip>

      <div className="flex flex-col flex-1">
        {body && body.trim().length > 0 && (
          !showTools ? (
            <>
              <Content
                content={body}
                preload={status === "streaming" ? "none" : "auto"}
                onPromptClick={onPromptClick}
              />
              {content && typeof content !== 'string' && (
                <MediaArtifacts
                  content={content}
                  preload={status === "streaming" ? "none" : "metadata"}
                />
              )}
            </>
          ) : (
            <div className="whitespace-pre-wrap">{body}</div>
          )
        )}
      </div>
    </div>
  );
};

export default HumanMessage;
