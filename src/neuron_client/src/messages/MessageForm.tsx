import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { useAppSelector } from "../hooks";
import { getSocket } from "../slices/socketSlice";
import { CornerDownLeft, Mic, Paperclip } from "lucide-react";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { getActiveProviderId } from "../slices/providersSlice";
interface MessageFormProps {
  isLoading?: boolean;
  onSubmit: (value: string) => void;
  className?: string;
}

export default function MessageForm({
  isLoading = false,
  onSubmit,
  className = "",
}: MessageFormProps) {
  const socket = useAppSelector(getSocket);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activeProviderId = useAppSelector(getActiveProviderId);
  const [value, setValue] = useState("");
  const { threadId } = useParams();
  const handleSubmit = (
    e:
      | React.FormEvent<HTMLFormElement>
      | React.FormEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    e.preventDefault();
    if (!socket || value.trim().length === 0 || !activePersonalityId) {
      return;
    }
    onSubmit(value);
    socket.sendMessage({
      type: "PostMessage",
      thread_id: threadId,
      prompt: value,
      personality_id: activePersonalityId,
      provider_id: activeProviderId,
    });
    setValue("");
  };
  return (
    <form className={`${className}`} onSubmit={handleSubmit}>
      <Label htmlFor="message" className="sr-only">
        Message
      </Label>
      <Textarea
        id="message"
        placeholder="Type your message here..."
        className="min-h-12 bg-secondary resize-none border-0 p-3 shadow-none focus-visible:ring-0"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isLoading}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            handleSubmit(e);
          }
        }}
      />
      <div className="flex items-center pt-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon">
              <Paperclip className="size-4" />
              <span className="sr-only">Attach file</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">Attach File</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon">
              <Mic className="size-4" />
              <span className="sr-only">Use Microphone</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">Use Microphone</TooltipContent>
        </Tooltip>
        <Button
          onClick={handleSubmit}
          type="submit"
          size="sm"
          className="ml-auto gap-1.5"
        >
          Send Message
          <CornerDownLeft className="size-3.5" />
        </Button>
      </div>
    </form>
  );
}
