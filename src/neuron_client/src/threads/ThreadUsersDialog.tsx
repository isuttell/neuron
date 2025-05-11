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
import { ThreadUser } from "@/types/thread";
import { User } from "@/types/user";
import { Trash2, Users } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  addUserByEmail,
  fetchThreadUsers,
  removeThreadUser,
  updateThreadUserRole,
} from "../actions/threadActions";
import { useAppDispatch, useAppSelector } from "../hooks";
import { useToast } from "../hooks/use-toast";
import { getThreadUsers } from "../slices/threadsSlice";
import { getUsers } from "../slices/usersSlice";

interface ThreadUsersDialogProps {
  threadId: string;
}

export default function ThreadUsersDialog({
  threadId,
}: ThreadUsersDialogProps) {
  const dispatch = useAppDispatch();
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [addingUser, setAddingUser] = useState(false);
  const [email, setEmail] = useState("");
  const threadUsers = useAppSelector((state) =>
    getThreadUsers(state, threadId)
  );
  const users = useAppSelector(getUsers);

  const loadUsers = async () => {
    setLoading(true);
    try {
      await dispatch(fetchThreadUsers(threadId)).unwrap();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to load thread users",
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
  }, [open, threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddUserByEmail = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setAddingUser(true);
    try {
      await dispatch(addUserByEmail({ threadId, email })).unwrap();
      toast({
        title: "User added",
        description: "User has been added to the thread",
      });
      setEmail("");
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to add user",
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
      await dispatch(removeThreadUser({ threadId, userId })).unwrap();
      toast({
        title: "User removed",
        description: "User has been removed from the thread",
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to remove user",
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    }
  };

  const handleRoleChange = async (userId: string, role: string) => {
    try {
      await dispatch(updateThreadUserRole({ threadId, userId, role })).unwrap();
      toast({
        title: "Role updated",
        description: `User role has been updated to ${role}`,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Failed to update role",
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
    <Dialog open={open} onOpenChange={setOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon">
              <Users className="m-3" />
              <span className="sr-only">Manage Thread Users</span>
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>Manage Thread Users</TooltipContent>
      </Tooltip>
      <DialogContent className="max-w-[600px]">
        <DialogHeader className="mb-4">
          <DialogTitle>Manage Thread Users</DialogTitle>
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
            Users with access to this thread:
          </div>
          {loading ? (
            <div className="text-center py-4">Loading users...</div>
          ) : threadUsers.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              No users found
            </div>
          ) : (
            <div className="space-y-2">
              {threadUsers.map((threadUser: ThreadUser) => {
                const user = getUserDetails(threadUser.user_id);
                return (
                  <div
                    key={threadUser.user_id}
                    className="flex items-center justify-between p-2 border rounded-md"
                  >
                    <div className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        {user?.picture ? (
                          <AvatarImage src={user.picture} alt={user.nickname} />
                        ) : null}
                        <AvatarFallback>
                          {user?.nickname?.substring(0, 2) || "U"}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">
                          {user?.nickname || "Unknown"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {user?.email || ""}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Select
                        defaultValue={threadUser.role}
                        onValueChange={(value) =>
                          handleRoleChange(threadUser.user_id, value)
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
                        onClick={() => handleRemoveUser(threadUser.user_id)}
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
