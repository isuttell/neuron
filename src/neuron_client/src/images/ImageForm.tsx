import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CornerDownLeft } from "lucide-react";
import { useState } from "react";
import { useAppSelector } from "../hooks";
import { getSocket, getConnectionStatus } from "../slices/socketSlice";
import { WebSocketPayload } from "../types/websocket";

interface ImageFormProps {
  isLoading?: boolean;
  onSubmit?: (value: string) => void;
  className?: string;
}

export default function ImageForm({
  isLoading = false,
  onSubmit = () => {},
  className = "",
}: ImageFormProps) {
  const socket = useAppSelector(getSocket);
  const isConnected = useAppSelector(getConnectionStatus);
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (
    e:
      | React.FormEvent<HTMLFormElement>
      | React.FormEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    e.preventDefault();
    if (!socket || !isConnected || value.trim().length === 0 || isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    socket.sendMessage({
      type: "CreateImage",
      prompt: value,
    } as WebSocketPayload);
    onSubmit(value);
    setTimeout(() => {
      setIsSubmitting(false);
    }, 1000);
  };
  return (
    <form className={`${className}`} onSubmit={handleSubmit}>
      <Label htmlFor="Prompt" className="sr-only">
        Prompt
      </Label>
      <Textarea
        id="Prompt"
        placeholder="Type your prompt here..."
        className="min-h-12 bg-secondary resize-none border-0 p-3 shadow-none focus-visible:ring-0"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isLoading || !isConnected}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            handleSubmit(e);
          }
        }}
      />
      <div className="flex items-center pt-1">
        <Button
          onClick={handleSubmit}
          type="submit"
          size="sm"
          className="ml-auto gap-1.5"
          disabled={isSubmitting || !isConnected}
        >
          Submit
          <CornerDownLeft className="size-3.5" />
        </Button>
      </div>
    </form>
  );
}
