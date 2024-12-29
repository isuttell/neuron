import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { useAppSelector } from "../hooks";
import { CornerDownLeft } from "lucide-react";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { Spinner } from "@/components/ui/spinner";
import { sendMessage } from "../actions/messageActions";
import { useAppDispatch } from "../hooks";
import Counter from "../lib/Counter";
import { cn } from "@/lib/utils";
interface MessageFormProps {
  status: string;
  disabled?: boolean;
  onSubmit: (value: string) => void;
  className?: string;
  lastMessageAt?: number;
}

const StatusMap = {
  error: "Error",
  idle: "Idle",
  streaming: "Streaming",
  thinking: "Thinking",
  tools: "Tools",
  update_memory: "Memory",
  update_title: "Title",
};

const getStatusMessage = (status: string) => {
  return Array.from(
    new Set(
      status
        .split(",")
        .sort((a, b) => {
          if (a.trim() === "thinking") return -1;
          if (b.trim() === "thinking") return 1;
          if (a.trim() === "tools") return -1;
          if (b.trim() === "tools") return 1;
          return a.localeCompare(b);
        })
        .map((value) =>
          typeof StatusMap[value as keyof typeof StatusMap] === "string"
            ? StatusMap[value as keyof typeof StatusMap]
            : value.replace(/_/g, " ").trim()
        )
    )
  ).map((value) => (
    <span
      key={value}
      className="text-sm text-muted-foreground capitalize inline-flex items-center rounded-md bg-muted px-2 py-1 font-medium ring-1 ring-inset ring-gray-100/10"
    >
      {value}
    </span>
  ));
};

export default function MessageForm({
  disabled = false,
  status,
  onSubmit,
  className = "",
  lastMessageAt,
}: MessageFormProps) {
  const dispatch = useAppDispatch();
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
    if (value.trim().length === 0 || !activePersonalityId || !threadId) {
      return;
    }
    onSubmit(value);
    dispatch(
      sendMessage({
        threadId,
        prompt: value,
        personalityId: activePersonalityId,
      })
    );
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
        <div className="flex gap-1 flex-row">{getStatusMessage(status)}</div>
        <div className="flex-1" />
        <Button
          onClick={handleSubmit}
          type="submit"
          size="sm"
          className={cn(
            "ml-auto gap-1.5",
            status === "idle"
              ? "bg-accent text-accent-foreground"
              : "bg-primary text-primary-foreground"
          )}
          disabled={disabled}
        >
          {status !== "idle" ? (
            <>
              {lastMessageAt && (
                <Counter
                  className="text-xs text-gray-500 pr-1"
                  startDate={lastMessageAt}
                />
              )}
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
