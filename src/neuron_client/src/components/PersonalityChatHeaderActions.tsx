import { MoreHorizontal, UserPen, Trash } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { usePersonalityPermissions } from "@/hooks/usePersonalityPermissions";
import { useAppDispatch } from "@/hooks";
import { clearPersonalityMessages } from "@/actions/personalityChatActions";
import { toast } from "sonner";

interface PersonalityChatHeaderActionsProps {
  personalityId: string;
  onEditPersonality: () => void;
}

export default function PersonalityChatHeaderActions({
  personalityId,
  onEditPersonality,
}: PersonalityChatHeaderActionsProps) {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);

  const {
    canManage: canManagePersonality
  } = usePersonalityPermissions(personalityId);

  const handleClearChat = async () => {
    try {
      await dispatch(clearPersonalityMessages(personalityId)).unwrap();
      toast.success("Chat history cleared");
    } catch (error) {
      toast.error("Failed to clear chat history", {
        description: error instanceof Error ? error.message : "An unexpected error occurred",
      });
    }
    setOpen(false);
  };

  // Hide component if user has no permissions
  if (!canManagePersonality) {
    return null;
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="size-4" />
              <span className="sr-only">More actions</span>
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent>More actions</TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end">
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            onEditPersonality();
            setOpen(false);
          }}
        >
          <UserPen className="size-4" />
          Edit Personality
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            handleClearChat();
          }}
          className="text-destructive focus:text-destructive"
        >
          <Trash className="size-4" />
          Clear Chat History
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
