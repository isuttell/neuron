import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ScrollText } from "lucide-react";
import { useAppSelector } from "@/hooks";
import { selectPromptsByPersonality } from "@/slices/promptsSlice";
import { getActivePersonalityId } from "@/slices/personalitiesSlice";
import { useEffect } from "react";
import { useAppDispatch } from "@/hooks";
import { fetchPrompts } from "@/slices/promptsSlice";

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
  }, [activePersonalityId]);

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
          prompts.map((prompt) => (
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
