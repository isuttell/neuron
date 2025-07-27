import { MoreHorizontal, Users, Trash } from "lucide-react";
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
import { usePersonalityRoomPermissions } from "@/hooks/usePersonalityRoomPermissions";

interface PersonalityRoomHeaderActionsProps {
  personalityId: string;
  roomId: string;
  onManageUsers: () => void;
  onDeleteRoom: () => void;
}

export default function PersonalityRoomHeaderActions({
  personalityId,
  roomId,
  onManageUsers,
  onDeleteRoom,
}: PersonalityRoomHeaderActionsProps) {
  const [open, setOpen] = useState(false);
  const {
    canManageUsers,
    canDelete,
    hasAnyActions,
  } = usePersonalityRoomPermissions(personalityId, roomId);

  // Hide component if user has no permissions
  if (!hasAnyActions) {
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
            {canManageUsers && <DropdownMenuSeparator />}
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setOpen(false);
                // Small delay to ensure dropdown closes before dialog opens
                setTimeout(onDeleteRoom, 0);
              }}
              className="text-destructive focus:text-destructive"
            >
              <Trash className="size-4" />
              Delete Room
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
