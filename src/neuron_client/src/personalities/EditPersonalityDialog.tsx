import React, { useState, useEffect } from "react";
import { UserPen, UserPlus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Personality } from "../slices/personalitiesSlice";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { getActiveProviderId } from "../slices/providersSlice";
import { getSocket } from "../slices/socketSlice";
import { useNavigate } from "react-router-dom";

interface EditPersonalityDialogProps {
  personality?: Personality;
}

const EditPersonalityDialog: React.FC<EditPersonalityDialogProps> = ({
  personality,
}) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(personality?.name || "");
  const [context, setContext] = useState(personality?.context || "");
  const [memory, setMemory] = useState(personality?.memory || "");
  const [loading, setLoading] = useState(false);
  const socket = useAppSelector(getSocket);
  const activeProviderId = useAppSelector(getActiveProviderId);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProviderId || !socket || loading) {
      return;
    }
    setLoading(true);
    dispatch({
      type: personality
        ? "socket/UpdatePersonality"
        : "socket/CreatePersonality",
      id: personality?.id,
      name,
      context,
      memory,
      provider_id: activeProviderId,
    });
    if (!personality) {
      socket.once("personality", ({ personality }) => {
        setLoading(false);
        setOpen(false);
        navigate(`/personality/${personality.id}`);
      });
    } else {
      setOpen(false);
    }
  };
  const handleDelete = (e: React.FormEvent) => {
    e.preventDefault();
    dispatch({
      type: "socket/DeletePersonality",
      personality_id: personality?.id,
    });
    setOpen(false);
  };
  useEffect(() => {
    setName(personality?.name || "");
    setContext(personality?.context || "");
    setMemory(personality?.memory || "");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          {personality ? (
            <UserPen className="size-4" />
          ) : (
            <UserPlus className="size-4" />
          )}
          <span className="sr-only">
            {personality ? "Edit" : "Create"} Personality
          </span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader className="mb-4">
            <DialogTitle>
              {personality ? "Edit" : "Create"} Personality
            </DialogTitle>
          </DialogHeader>
          <div className="mb-4">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name"
            />
          </div>
          <div className="mb-4">
            <Textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Context"
            />
          </div>
          <div className="mb-4">
            <Textarea
              value={memory}
              onChange={(e) => setMemory(e.target.value)}
              placeholder="Memory"
            />
          </div>
          <DialogFooter className="flex justify-end">
            <Button
              variant="destructive"
              onClick={handleDelete}
              type="submit"
              className="ml-2"
            >
              Delete
            </Button>
            <div className="flex-1" />
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleSubmit}
              type="submit"
              disabled={loading}
              className="ml-2"
            >
              {loading ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EditPersonalityDialog;
