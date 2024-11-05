import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { useAppSelector } from "../hooks";
import { getSocket } from "../slices/socketSlice";
import { CornerDownLeft } from "lucide-react";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { getActiveProviderId } from "../slices/providersSlice";
import { Spinner } from "@/components/ui/spinner";
interface MessageFormProps {
  isLoading?: boolean;
  disabled?: boolean;
  onSubmit: (value: string) => void;
  className?: string;
}

export default function MessageForm({
  disabled = false,
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
    if (
      isLoading ||
      !socket ||
      value.trim().length === 0 ||
      !activePersonalityId
    ) {
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
        className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 p-4"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            handleSubmit(e);
          }
        }}
      />
      <div className="flex items-center pt-2">
        <Button
          onClick={handleSubmit}
          type="submit"
          size="sm"
          className="ml-auto gap-1.5"
          disabled={isLoading || disabled}
        >
          {isLoading ? (
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
