import React, { useState } from "react";
import { ListPlus } from "lucide-react";
import { useAppDispatch } from "@/hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { createMediaList } from "@/slices/mediaListsSlice";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const NewMediaListDialog = () => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Name required", {
        description: "Please enter a name for your list",
      });
      return;
    }

    setLoading(true);
    try {
      await dispatch(createMediaList({ name, description })).unwrap();
      toast("Success", {
        description: "Media list created successfully",
      });
      setOpen(false);
      setName("");
      setDescription("");
    } catch (error) {
      toast.error("Failed to create list", {
        description:
          error instanceof Error
            ? error.message
            : "An unexpected error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon">
              <ListPlus className="m-3" />
              <span className="sr-only">New List</span>
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>Create New List</TooltipContent>
      </Tooltip>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader className="mb-4">
            <DialogTitle>Create New List</DialogTitle>
          </DialogHeader>
          <div className="mb-4">
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="List Name"
              required
            />
          </div>
          <div className="mb-4">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description"
            />
          </div>
          <DialogFooter className="flex justify-end">
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" className="ml-2" disabled={loading}>
              {loading ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default NewMediaListDialog;
