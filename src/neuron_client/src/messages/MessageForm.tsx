import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { useAppSelector } from "../hooks";
import { getSocket } from "../slices/socketSlice";
import { CornerDownLeft } from "lucide-react";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { Spinner } from "@/components/ui/spinner";

interface MessageFormProps {
  status: string;
  disabled?: boolean;
  onSubmit: (value: string) => void;
  className?: string;
}

const getStatusMessage = (status: string) => {
  if (status === "thinking") {
    return "Thinking...";
  } else if (status === "tools") {
    return "Working...";
  } else if (status === "streaming") {
    return "Streaming...";
  } else {
    return "Idle";
  }
};

export default function MessageForm({
  disabled = false,
  status,
  onSubmit,
  className = "",
}: MessageFormProps) {
  const socket = useAppSelector(getSocket);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
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
        className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            handleSubmit(e);
          }
        }}
      />
      <div className="flex items-center pt-2">
        <div className="text-sm text-gray-500">{getStatusMessage(status)}</div>
        <div className="flex-1" />
        <Button
          onClick={handleSubmit}
          type="submit"
          size="sm"
          className="ml-auto gap-1.5"
          disabled={disabled}
        >
          {status !== "idle" ? (
            <>
              <Spinner className="size-3.5" />
            </>
          ) : (
            <>
              Send Message
              <CornerDownLeft className="size-3.5" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
