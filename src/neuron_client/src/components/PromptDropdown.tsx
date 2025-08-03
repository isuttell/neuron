import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAppDispatch, useAppSelector } from "@/hooks";
import {
  fetchPrompts,
  selectPromptsByPersonality,
} from "@/slices/promptsSlice";
import { ScrollText } from "lucide-react";
import { useEffect } from "react";

interface PromptDropdownProps {
  onSelectPrompt: (promptText: string) => void;
  disabled?: boolean;
  personalityId?: string;
}

export function PromptDropdown({
  onSelectPrompt,
  disabled = false,
  personalityId,
}: PromptDropdownProps) {
  const dispatch = useAppDispatch();
  const prompts = useAppSelector((state) =>
    personalityId
      ? selectPromptsByPersonality(state, personalityId)
      : []
  );

  useEffect(() => {
    if (personalityId) {
      dispatch(fetchPrompts(personalityId));
    }
  }, [personalityId, dispatch]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="mr-2 size-10"
          disabled={disabled}
        >
          <ScrollText className="size-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[200px]">
        <DropdownMenuLabel>Prompts</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {prompts.length === 0 ? (
          <DropdownMenuItem disabled>No prompts available</DropdownMenuItem>
        ) : (
          [...prompts]
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((prompt) => (
              <DropdownMenuItem
                key={prompt.id}
                onClick={() => onSelectPrompt(prompt.text)}
              >
                {prompt.name}
              </DropdownMenuItem>
            ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
