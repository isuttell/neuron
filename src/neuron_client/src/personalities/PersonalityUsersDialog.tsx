import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { User } from "@/types/user";
import { UserWithRole } from "@/slices/personalitiesSlice.d";
import { Trash2, Users } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  addPersonalityUser,
  fetchPersonalityUsers,
  removePersonalityUser,
  updatePersonalityUserRole,
} from "../actions/personalityActions";
import { useAppDispatch, useAppSelector } from "../hooks";
import { toast } from "sonner";
import { getPersonalityUsers } from "../slices/personalitiesSlice";
import { getUsers } from "../slices/usersSlice";

interface PersonalityUsersDialogProps {
  personalityId: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export default function PersonalityUsersDialog({
  personalityId,
  open: controlledOpen,
  onOpenChange,
  trigger,
}: PersonalityUsersDialogProps) {
  const dispatch = useAppDispatch();
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);

  // Use controlled open if provided, otherwise use internal state
  const isControlled = controlledOpen !== undefined;
  const open = isControlled ? controlledOpen : uncontrolledOpen;

  const handleOpenChange = (newOpen: boolean) => {
    if (!isControlled) {
      setUncontrolledOpen(newOpen);
    }
    onOpenChange?.(newOpen);
  };
  const [loading, setLoading] = useState(false);
  const [addingUser, setAddingUser] = useState(false);
  const [email, setEmail] = useState("");
  const personalityUsers = useAppSelector((state) =>
    getPersonalityUsers(state, personalityId)
  );
  const users = useAppSelector(getUsers);

  const loadUsers = async () => {
    setLoading(true);
    try {
      await dispatch(fetchPersonalityUsers(personalityId)).unwrap();
    } catch (error) {
      toast.error("Failed to load personality users", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadUsers();
    }
  }, [open, personalityId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddUserByEmail = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setAddingUser(true);
    try {
      await dispatch(addPersonalityUser({ personalityId, email })).unwrap();
      toast("User added", {
        description: "User has been added to the personality",
      });
      setEmail("");
    } catch (error) {
      toast.error("Failed to add user", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    } finally {
      setAddingUser(false);
    }
  };

  const handleRemoveUser = async (userId: string) => {
    try {
      await dispatch(removePersonalityUser({ personalityId, userId })).unwrap();
      toast("User removed", {
        description: "User has been removed from the personality",
      });
    } catch (error) {
      toast.error("Failed to remove user", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
  };

  const handleRoleChange = async (userId: string, role: string) => {
    try {
      await dispatch(updatePersonalityUserRole({ personalityId, userId, role })).unwrap();
      toast("Role updated", {
        description: `User role has been updated to ${role}`,
      });
    } catch (error) {
      toast.error("Failed to update role", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
  };

  const getUserDetails = (userId: string): User | undefined => {
    return users[userId];
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {trigger !== undefined ? (
        trigger
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon">
                <Users className="m-3" />
                <span className="sr-only">Manage Personality Users</span>
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>Manage Personality Users</TooltipContent>
        </Tooltip>
      )}
      <DialogContent className="max-w-[600px]">
        <DialogHeader className="mb-4">
          <DialogTitle>Manage Personality Users</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <form onSubmit={handleAddUserByEmail} className="flex gap-2 mb-4">
            <Input
              type="email"
              placeholder="Add user by email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={addingUser}
              className="flex-1"
            />
            <Button type="submit" disabled={addingUser || !email.trim()}>
              {addingUser ? "Adding..." : "Add"}
            </Button>
          </form>

          <div className="text-sm text-muted-foreground mb-2">
            Users with access to this personality:
          </div>
          {loading ? (
            <div className="text-center py-4">Loading users...</div>
          ) : personalityUsers.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              No users found
            </div>
          ) : (
            <div className="space-y-2">
              {personalityUsers.map((personalityUser: UserWithRole) => {
                const user = getUserDetails(personalityUser.id || personalityUser.user_id);
                return (
                  <div
                    key={personalityUser.id || personalityUser.user_id}
                    className="flex items-center justify-between p-2 border rounded-md"
                  >
                    <div className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        {user?.picture ? (
                          <AvatarImage src={user.picture} alt={user.nickname} />
                        ) : null}
                        <AvatarFallback>
                          {user?.nickname?.substring(0, 2) || personalityUser.nickname?.substring(0, 2) || "U"}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">
                          {user?.nickname || personalityUser.nickname || "Unknown"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {user?.email || personalityUser.email || ""}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Select
                        defaultValue={personalityUser.role}
                        onValueChange={(value) =>
                          handleRoleChange(personalityUser.id || personalityUser.user_id, value)
                        }
                      >
                        <SelectTrigger className="w-[100px]">
                          <SelectValue placeholder="Role" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="admin">Admin</SelectItem>
                          <SelectItem value="user">User</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveUser(personalityUser.id || personalityUser.user_id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <DialogFooter className="flex justify-end">
          <DialogClose asChild>
            <Button type="button">Close</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
