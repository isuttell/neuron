import { useState, useEffect } from "react";
import { Check, ChevronsUpDown, User as UserIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { User } from "@/types/user";

interface UserSearchComboboxProps {
  availableUsers: User[];
  excludeUsers?: User[]; // Users to exclude from the search (already added)
  onUserSelect: (user: User) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export default function UserSearchCombobox({
  availableUsers,
  excludeUsers = [],
  onUserSelect,
  placeholder = "Search users...",
  disabled = false,
  className,
}: UserSearchComboboxProps) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  // Filter out users that are already added
  const excludeUserIds = new Set(excludeUsers.map(user => user.id));
  const filteredUsers = availableUsers.filter(user => !excludeUserIds.has(user.id));

  const selectedUser = filteredUsers.find((user) => user.id === value);

  // Call onUserSelect when a value is selected
  useEffect(() => {
    if (value && selectedUser) {
      onUserSelect(selectedUser);
      setValue(""); // Clear after selection
    }
  }, [value, selectedUser]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
  };

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn("w-full justify-between", className)}
          disabled={disabled}
        >
          {selectedUser ? (
            <div className="flex items-center gap-2">
              <Avatar className="h-6 w-6">
                {selectedUser.picture ? (
                  <AvatarImage src={selectedUser.picture} alt={selectedUser.nickname} />
                ) : null}
                <AvatarFallback className="text-xs">
                  {selectedUser.nickname?.substring(0, 2) || <UserIcon className="h-3 w-3" />}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col items-start">
                <span className="font-medium">{selectedUser.nickname}</span>
                <span className="text-xs text-muted-foreground">{selectedUser.email}</span>
              </div>
            </div>
          ) : (
            placeholder
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start" >
        <Command>
          <CommandInput placeholder="Search users..." />
          <CommandList>
            <CommandEmpty>No users found.</CommandEmpty>
            <CommandGroup>
              {filteredUsers.map((user) => (
                <CommandItem
                  key={user.id}
                  value={user.id}
                  onSelect={(currentValue) => {
                    setValue(currentValue === value ? "" : currentValue);
                    setOpen(false);
                  }}
                  className="flex items-center gap-2 py-2"
                >
                  <Avatar className="h-8 w-8">
                    {user.picture ? (
                      <AvatarImage src={user.picture} alt={user.nickname} />
                    ) : null}
                    <AvatarFallback className="text-xs">
                      {user.nickname?.substring(0, 2) || <UserIcon className="h-4 w-4" />}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col flex-1">
                    <span className="font-medium">
                      {user.nickname || "Unknown User"}
                    </span>
                    <span className="text-xs text-muted-foreground">{user.email}</span>
                  </div>
                  <Check
                    className={cn(
                      "ml-auto h-4 w-4",
                      value === user.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
