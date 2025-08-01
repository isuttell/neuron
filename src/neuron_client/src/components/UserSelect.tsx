import { useState } from "react";
import { User as UserIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { User } from "@/types/user";

interface UserSelectProps {
  availableUsers: User[];
  excludeUsers?: User[]; // Users to exclude from the search (already added)
  onUserSelect: (user: User) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export default function UserSelect({
  availableUsers,
  excludeUsers = [],
  onUserSelect,
  placeholder = "Select a user...",
  disabled = false,
  className,
}: UserSelectProps) {
  const [value, setValue] = useState("");

  // Filter out users that are already added
  const excludeUserIds = new Set(excludeUsers.map(user => user.id));
  const filteredUsers = availableUsers.filter(user => !excludeUserIds.has(user.id));

  const handleValueChange = (userId: string) => {
    const user = filteredUsers.find(u => u.id === userId);
    if (user) {
      onUserSelect(user);
      // Clear immediately after selection
      setValue("");
    }
  };

  return (
    <Select value={value} onValueChange={handleValueChange} disabled={disabled}>
      <SelectTrigger className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {filteredUsers.length === 0 ? (
          <div className="py-2 px-3 text-sm text-muted-foreground">No users available</div>
        ) : (
          filteredUsers.map((user) => (
            <SelectItem key={user.id} value={user.id}>
              <div className="flex items-center gap-2">
                <Avatar className="h-6 w-6">
                  {user.picture ? (
                    <AvatarImage src={user.picture} alt={user.nickname} />
                  ) : null}
                  <AvatarFallback className="text-xs">
                    {user.nickname?.substring(0, 2) || <UserIcon className="h-3 w-3" />}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col items-start">
                  <span className="font-medium">{user.nickname || "Unknown User"}</span>
                  <span className="text-xs text-muted-foreground">{user.email}</span>
                </div>
              </div>
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  );
}
