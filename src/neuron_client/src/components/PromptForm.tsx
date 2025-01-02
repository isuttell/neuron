import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { useState } from "react";
import { Prompt } from "../slices/promptsSlice";

interface PromptFormProps {
  prompt?: Prompt;
  onSubmit: (values: { name: string; text: string }) => void;
  onCancel: () => void;
  disabled?: boolean;
}

export function PromptForm({
  prompt,
  onSubmit,
  onCancel,
  disabled,
}: PromptFormProps) {
  const [name, setName] = useState(prompt?.name || "");
  const [text, setText] = useState(prompt?.text || "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, text });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="name" className="text-sm font-medium">
          Name
        </label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter prompt name"
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="text" className="text-sm font-medium">
          Text
        </label>
        <Textarea
          id="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter prompt text"
          required
          className="min-h-[200px]"
        />
      </div>

      <div className="flex justify-end space-x-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={disabled}>
          {prompt ? "Update Prompt" : "Create Prompt"}
        </Button>
      </div>
    </form>
  );
}
