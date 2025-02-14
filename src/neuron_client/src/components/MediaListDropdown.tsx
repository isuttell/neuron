import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { ListPlus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppDispatch, useAppSelector } from "@/hooks";
import { selectAllMediaLists, addMediaToList } from "@/slices/mediaListsSlice";
import { useToast } from "@/hooks/use-toast";
import { buttonVariants } from "@/components/ui/button";

interface MediaListDropdownProps {
  mediaItemId: string;
  disabled?: boolean;
  variant?: "ghost" | "outline";
  size?: "sm" | "default" | "lg" | "icon";
}

export function MediaListDropdown({
  mediaItemId,
  disabled = false,
  variant = "ghost",
  size = "default",
}: MediaListDropdownProps) {
  const dispatch = useAppDispatch();
  const mediaLists = useAppSelector(selectAllMediaLists);
  const { toast } = useToast();

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger
            className={cn(buttonVariants({ variant, size }))}
            disabled={disabled || mediaLists.length === 0}
          >
            <ListPlus className="size-4" />
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent>Add to list</TooltipContent>
      </Tooltip>
      <DropdownMenuContent>
        <DropdownMenuLabel className="text-xs border-b">
          Add to list
        </DropdownMenuLabel>
        {mediaLists.map((list) => (
          <DropdownMenuItem
            key={list.id}
            onClick={(e) => {
              e.preventDefault();
              dispatch(
                addMediaToList({
                  listId: list.id,
                  mediaItemId,
                  index: null,
                })
              );
              toast({
                title: `Added to ${list.name}`,
              });
            }}
          >
            {list.name}
          </DropdownMenuItem>
        ))}
        {mediaLists.length === 0 && (
          <DropdownMenuItem disabled>No lists available</DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
