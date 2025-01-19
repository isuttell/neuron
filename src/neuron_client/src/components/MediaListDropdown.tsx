import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ListPlus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/hooks";
import { selectAllMediaLists, addMediaToList } from "@/slices/mediaListsSlice";
import { useToast } from "@/hooks/use-toast";

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
      <DropdownMenuTrigger asChild>
        <Button
          size={size}
          variant={variant}
          disabled={disabled || mediaLists.length === 0}
        >
          <ListPlus className="size-4" />
        </Button>
      </DropdownMenuTrigger>
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
