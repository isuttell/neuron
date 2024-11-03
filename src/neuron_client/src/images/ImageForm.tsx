import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { useAppSelector } from "../hooks";
import { getSocket } from "../slices/socketSlice";
import { CornerDownLeft } from "lucide-react";

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
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (
    e:
      | React.FormEvent<HTMLFormElement>
      | React.FormEvent<HTMLButtonElement>
      | React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    e.preventDefault();
    if (!socket || value.trim().length === 0 || isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    socket.sendMessage({
      type: "CreateImage",
      prompt: value,
    });
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
        disabled={isLoading}
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
          disabled={isSubmitting}
        >
          Submit
          <CornerDownLeft className="size-3.5" />
        </Button>
      </div>
    </form>
  );
}
