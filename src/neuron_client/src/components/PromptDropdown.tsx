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
import { getActivePersonalityId } from "@/slices/personalitiesSlice";
import {
  fetchPrompts,
  selectPromptsByPersonality,
} from "@/slices/promptsSlice";
import { ScrollText } from "lucide-react";
import { useEffect } from "react";

interface PromptDropdownProps {
  onSelectPrompt: (promptText: string) => void;
  disabled?: boolean;
}

export function PromptDropdown({
  onSelectPrompt,
  disabled = false,
}: PromptDropdownProps) {
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const dispatch = useAppDispatch();
  const prompts = useAppSelector((state) =>
    activePersonalityId
      ? selectPromptsByPersonality(state, activePersonalityId)
      : []
  );

  useEffect(() => {
    if (activePersonalityId) {
      dispatch(fetchPrompts(activePersonalityId));
    }
  }, [activePersonalityId, dispatch]);

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
