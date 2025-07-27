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
import { Label } from "@/components/ui/label";
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
import { PersonalityRoomUser } from "@/types/personalityRoom";
import { User } from "@/types/user";
import { Trash2, Users } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import * as personalityRoomActions from "../actions/personalityRoomActions";
import {
  removePersonalityRoomUser,
  updatePersonalityRoom,
  updatePersonalityRoomUser,
} from "../actions/personalityRoomActions";
import { api } from "@/lib/api";
import { useAppDispatch, useAppSelector } from "../hooks";
import { toast } from "sonner";
import { getPersonalityRoom, getRoomUsers } from "../slices/personalityRoomSlice";
import { getUsers } from "../slices/usersSlice";

interface PersonalityRoomUsersDialogProps {
  personalityId: string;
  roomId: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: React.ReactNode;
}

export default function PersonalityRoomUsersDialog({
  personalityId,
  roomId,
  open: controlledOpen,
  onOpenChange,
  trigger,
}: PersonalityRoomUsersDialogProps) {
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
  const [updatingRoomType, setUpdatingRoomType] = useState(false);

  const room = useAppSelector((state) => getPersonalityRoom(state, roomId));
  const roomUsers = useAppSelector((state) => getRoomUsers(state, roomId));
  const users = useAppSelector(getUsers);

  useEffect(() => {
    if (open && personalityId && roomId) {
      // Room data should already be loaded from the parent component
      setLoading(false);
    }
  }, [open, personalityId, roomId]);

  const handleAddUserByEmail = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setAddingUser(true);
    try {
      // Use the email endpoint instead of the regular user endpoint
      await api.post<{ user: User; personality_room_user: PersonalityRoomUser }>(
        `/personality-rooms/${personalityId}/rooms/${roomId}/users/email`,
        { email }
      );

      // Dispatch action to update the store with the new user
      await dispatch(personalityRoomActions.getPersonalityRoom({ personalityId, roomId }));

      toast("User added", {
        description: "User has been added to the room",
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
      await dispatch(removePersonalityRoomUser({ personalityId, roomId, userId })).unwrap();
      toast("User removed", {
        description: "User has been removed from the room",
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

  const handleRoomTypeChange = async (newType: string) => {
    if (!room) return;

    setUpdatingRoomType(true);
    try {
      await dispatch(updatePersonalityRoom({
        personalityId,
        roomId,
        data: { type: newType }
      })).unwrap();
      toast("Room type updated", {
        description: `Room is now ${newType}`,
      });
    } catch (error) {
      toast.error("Failed to update room type", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    } finally {
      setUpdatingRoomType(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await dispatch(updatePersonalityRoomUser({
        personalityId,
        roomId,
        userId,
        data: { role: newRole }
      })).unwrap();
      toast("Role updated", {
        description: `User role has been updated to ${newRole}`,
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

  if (!room) {
    return null;
  }

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
                <span className="sr-only">Manage Room Users</span>
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>Manage Room Users</TooltipContent>
        </Tooltip>
      )}
      <DialogContent className="max-w-[600px]">
        <DialogHeader className="mb-4">
          <DialogTitle>Manage Room: {room.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          {/* Room Type Section */}
          <div className="space-y-2">
            <Label htmlFor="room-type">Room Type</Label>
            <Select
              value={room.type}
              onValueChange={handleRoomTypeChange}
              disabled={updatingRoomType}
            >
              <SelectTrigger id="room-type">
                <SelectValue placeholder="Select room type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="private">Private</SelectItem>
                <SelectItem value="shared">Shared</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {room.type === "private"
                ? "Only invited users can access this room"
                : "Room is visible to all personality users"}
            </p>
          </div>

          {/* Add User Section */}
          <div className="space-y-2">
            <Label htmlFor="add-user">Add User</Label>
            <form onSubmit={handleAddUserByEmail} className="flex gap-2">
              <Input
                id="add-user"
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
          </div>

          {/* Users List Section */}
          <div className="space-y-2">
            <Label>Room Members</Label>
            {loading ? (
              <div className="text-center py-4">Loading users...</div>
            ) : roomUsers.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                No users found
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {roomUsers.map((roomUser: PersonalityRoomUser) => {
                  const user = getUserDetails(roomUser.user_id);
                  return (
                    <div
                      key={roomUser.user_id}
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
                            {user?.email || roomUser.user_id}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Select
                          defaultValue={roomUser.role}
                          onValueChange={(value) =>
                            handleRoleChange(roomUser.user_id, value)
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
                          onClick={() => handleRemoveUser(roomUser.user_id)}
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
