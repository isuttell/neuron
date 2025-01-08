import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { useState } from "react";
import { Prompt } from "../slices/promptsSlice";
import { Personality, getPersonalities } from "../slices/personalitiesSlice";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { useAppSelector } from "../hooks";

interface PromptFormProps {
  prompt?: Prompt;
  onSubmit: (values: {
    name: string;
    text: string;
    personalityId?: string;
  }) => void;
  onCancel: () => void;
  disabled?: boolean;
}

export function PromptForm({
  prompt,
  onSubmit,
  onCancel,
  disabled,
}: PromptFormProps) {
  const personalities = useAppSelector(getPersonalities);
  const [name, setName] = useState(prompt?.name || "");
  const [text, setText] = useState(prompt?.text || "");
  const [personalityId, setPersonalityId] = useState(
    prompt?.personality_id || ""
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, text, personalityId: personalityId || undefined });
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

      {/* <div className="space-y-2">
        <label htmlFor="personality" className="text-sm font-medium">
          Personality
        </label>
        <Select value={personalityId} onValueChange={setPersonalityId}>
          <SelectTrigger>
            <SelectValue placeholder="Select a personality" />
          </SelectTrigger>
          <SelectContent>
            {personalities.slice().map((personality) => (
              <SelectItem key={personality.id} value={personality.id}>
                {personality.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div> */}

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
