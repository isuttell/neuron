import React, { useState } from "react";
import { Bot, ChevronDown, ChevronUp } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import Content from "./Content";
import Citations from "./Citations";
import MediaArtifacts from "./MediaArtifacts";

interface AssistantMessageProps {
  textContent: string;
  thinkingContent?: string;
  citations?: Array<{
    type: "char_location";
    cited_text: string;
    document_index: number;
    document_title: string;
    start_char_index: number;
    end_char_index: number;
  }>;
  content?: unknown[] | string;
  showTools: boolean;
  status?: string;
  onPromptClick?: (prompt: string) => void;
}

const AssistantMessage: React.FC<AssistantMessageProps> = ({
  textContent,
  thinkingContent,
  citations,
  content,
  showTools,
  status,
  onPromptClick,
}) => {
  const [isThinkingOpen, setIsThinkingOpen] = useState(false);

  let body = textContent;
  const isThinking = status === "streaming" && body.trim().length === 0;
  const hasThinking = thinkingContent && thinkingContent.trim().length > 0;

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
        <TooltipContent side="right">AI</TooltipContent>
      </Tooltip>

      <div className="flex flex-col flex-1">
        {hasThinking && (
          <Collapsible
            open={isThinkingOpen}
            onOpenChange={setIsThinkingOpen}
            className="mb-4 border bg-zinc-900 px-4 py-2 rounded-md"
          >
            <CollapsibleTrigger asChild>
              <div className="flex items-center justify-between cursor-pointer">
                <div className="text-sm font-medium italic flex items-center">
                  {isThinking ? "Thinking..." : "Thoughts"}
                </div>
                <button className="rounded-full p-1 hover:bg-muted">
                  {isThinkingOpen ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-4 mb-2 text-sm text-muted-foreground whitespace-pre-wrap">
                {thinkingContent}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {body && body.trim().length > 0 ? (
          !showTools ? (
            <>
              <Content
                content={body}
                preload={status === "streaming" ? "none" : "auto"}
                onPromptClick={onPromptClick}
              />
              {citations && citations.length > 0 && (
                <Citations citations={citations} />
              )}
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
        ) : isThinking ? (
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-[250px]" />
            <Skeleton className="h-4 w-[200px]" />
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default AssistantMessage;
