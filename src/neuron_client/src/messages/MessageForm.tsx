import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { useAppDispatch } from "../hooks";
import { CornerDownLeft, Upload } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { postMessageByThread } from "../actions/messageActions";
import { cn } from "@/lib/utils";
import { useToast } from "../hooks/use-toast";
import { StatusMessage } from "./StatusMessage";
import { PromptDropdown } from "@/components/PromptDropdown";
import { Thread } from "../slices/threadsSlice";

interface MessageFormProps {
  disabled?: boolean;
  onSubmit?: (value: string) => void;
  className?: string;
  lastMessageAt?: number;
  thread: Thread;
}

export default function MessageForm({
  disabled = false,
  onSubmit,
  className = "",
  thread,
}: MessageFormProps) {
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const [value, setValue] = useState("");
  const { threadId } = useParams();
  const [file, setFile] = useState<File | undefined>(undefined);
  const handleSubmit = (
    e:
      | React.FormEvent<HTMLFormElement>
      | React.FormEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    e.preventDefault();
    if (value.trim().length === 0 || !threadId) {
      return;
    }
    onSubmit?.(value);
    setValue("");
    setFile(undefined);
    dispatch(
      postMessageByThread({
        threadId,
        prompt: value,
        personalityId: thread.personality_id,
        file,
      })
    ).catch((error) => {
      toast({
        variant: "destructive",
        title: "Failed to send message",
        description: error?.message || "An unexpected error occurred",
      });
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFile(file);
      toast({
        title: "Attachment added",
        description: `${file.name} has been added to the message`,
      });
    }
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
      <div className="flex items-center gap-2 pt-2">
        <StatusMessage
          status={thread.status}
          tagClassName="text-sm text-muted-foreground capitalize inline-flex items-center rounded-md bg-muted px-2 py-1 font-medium ring-1 ring-inset ring-gray-100/10"
        />
        <div className="flex-1" />
        <Button
          type="button"
          size="sm"
          variant={file ? "default" : "outline"}
          disabled={disabled}
          onClick={() => {
            if (file) {
              setFile(undefined);
              toast({
                title: "Attachment removed",
              });
            } else {
              document.getElementById("file-upload")?.click();
            }
          }}
        >
          <Upload className="size-3.5" />
        </Button>
        <input
          id="file-upload"
          type="file"
          className="hidden"
          onChange={handleFileUpload}
          accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.md,.txt,.csv,.srt,.vtt,.mp3,.wav,.mp4,.heic,.heif"
        />
        <PromptDropdown
          disabled={disabled}
          onSelectPrompt={(promptText) => setValue(promptText)}
        />
        <Button
          onClick={handleSubmit}
          type="submit"
          size="sm"
          className={cn(
            "ml-auto gap-1.5",
            thread.status === "idle"
              ? "bg-accent text-accent-foreground"
              : "bg-primary text-primary-foreground"
          )}
          disabled={disabled || value.length === 0}
        >
          {thread.status !== "idle" ? (
            <>
              <Spinner className="size-3.5" />
            </>
          ) : (
            <>
              Send
              <CornerDownLeft className="size-3.5" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
