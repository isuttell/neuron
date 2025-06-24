import { MoreHorizontal, UserPen, Users, Trash, Bot } from "lucide-react";
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
import { useThreadPermissions } from "@/hooks/useThreadPermissions";
import { usePersonalityPermissions } from "@/hooks/usePersonalityPermissions";

interface ThreadHeaderActionsProps {
  threadId: string;
  showTools: boolean;
  onToggleTools: () => void;
  onEditPersonality: () => void;
  onManageUsers: () => void;
  onDeleteThread: () => void;
}

export default function ThreadHeaderActions({
  threadId,
  showTools,
  onToggleTools,
  onEditPersonality,
  onManageUsers,
  onDeleteThread,
}: ThreadHeaderActionsProps) {
  const [open, setOpen] = useState(false);
  const {
    thread,
    canManageUsers,
    canDelete,
    canViewSystemMessages,
    hasAnyActions: hasAnyThreadActions
  } = useThreadPermissions(threadId);

  // Get personality permissions for editing personality
  const {
    canManage: canManagePersonality
  } = usePersonalityPermissions(thread?.personality_id);

  // User should see the component if they have any thread actions OR personality actions
  const shouldShowComponent = hasAnyThreadActions || canManagePersonality;

  // Hide component if user has no permissions
  if (!shouldShowComponent) {
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
        {canViewSystemMessages && (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              onToggleTools();
              setOpen(false);
            }}
          >
            <Bot className="size-4" />
            {showTools ? "Hide" : "Show"} System Messages
          </DropdownMenuItem>
        )}
        {(canManagePersonality || canManageUsers) && canViewSystemMessages && (
          <DropdownMenuSeparator />
        )}
        {canManagePersonality && (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              setOpen(false);
              // Small delay to ensure dropdown closes before dialog opens
              setTimeout(onEditPersonality, 0);
            }}
          >
            <UserPen className="size-4" />
            Edit Personality
          </DropdownMenuItem>
        )}
        {canManageUsers && (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              setOpen(false);
              // Small delay to ensure dropdown closes before dialog opens
              setTimeout(onManageUsers, 0);
            }}
          >
            <Users className="size-4" />
            Manage Users
          </DropdownMenuItem>
        )}
        {canDelete && (
          <>
            {(canViewSystemMessages || canManagePersonality || canManageUsers) && (
              <DropdownMenuSeparator />
            )}
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setOpen(false);
                // Small delay to ensure dropdown closes before dialog opens
                setTimeout(onDeleteThread, 0);
              }}
              className="text-destructive focus:text-destructive"
            >
              <Trash className="size-4" />
              Delete Thread
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
