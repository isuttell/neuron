import React, { useState, useEffect } from "react";
import { UserPen, UserPlus } from "lucide-react";
import { useAppDispatch } from "../hooks";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { useNavigate } from "react-router-dom";
import {
  createPersonality,
  updatePersonality,
  deletePersonality,
} from "../actions/personalityActions";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Textarea } from "@/components/ui/textarea";
interface EditPersonalityDialogProps {
  personality?: Personality;
  default_tools?: string[];
}

const ToolSetLabels = {
  arxiv: "Arxiv",
  astro: "Astro",
  code_interpreter: "Code Interpreter",
  dice: "Dice",
  hd2: "Hell Divers 2",
  homeassistant: "Smart Home",
  image: "Image Generation",
  notifications: "Notifications",
  search: "Search",
  tts: "Audio Generation",
  weather: "Weather",
};

const EditPersonalityDialog: React.FC<EditPersonalityDialogProps> = ({
  personality,
  default_tools = ["image", "search", "tts"],
}) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(personality?.name || "");
  const [description, setDescription] = useState(
    personality?.description || ""
  );
  const [context, setContext] = useState(personality?.context || "");
  const [loading, setLoading] = useState(false);
  const [tool_set, setToolSet] = useState(
    (personality?.tool_set || "").split("+")
  );
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) {
      return;
    }
    setLoading(true);
    try {
      if (personality) {
        await dispatch(
          updatePersonality({
            id: personality.id,
            name,
            description,
            context,
            memory: personality.memory,
            tool_set: tool_set.length > 0 ? tool_set.join("+") : undefined,
          })
        ).unwrap();
      } else {
        const body = await dispatch(
          createPersonality({
            name,
            description,
            context,
            memory: "",
            tool_set: tool_set.length > 0 ? tool_set.join("+") : undefined,
          })
        ).unwrap();

        navigate(`/personality/${body.personality.id}`);
      }
      setOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.FormEvent) => {
    if (!personality) {
      return;
    }
    e.preventDefault();
    await dispatch(deletePersonality(personality.id));
    setOpen(false);
  };

  useEffect(() => {
    setName(personality?.name || "");
    setContext(personality?.context || "");
    setToolSet((personality?.tool_set || "").split("+"));
    setDescription(personality?.description || "");
  }, [open]);
  const active_tools = tool_set.length > 0 ? tool_set : default_tools;
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
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description"
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
            <div className="text-sm text-muted-foreground mb-2">Toolsets</div>

            <ToggleGroup
              className="flex-wrap gap-2 justify-start"
              type="multiple"
              variant="outline"
              defaultValue={active_tools}
              onValueChange={(value) => {
                setToolSet(
                  value.filter(
                    (val) =>
                      val !== "" && Object.keys(ToolSetLabels).includes(val)
                  )
                );
              }}
            >
              {Object.keys(ToolSetLabels).map((option) => (
                <ToggleGroupItem
                  key={option}
                  value={option}
                  defaultChecked={active_tools.includes(option)}
                  variant={
                    default_tools.includes(option) ? "default" : "outline"
                  }
                >
                  {ToolSetLabels[option as keyof typeof ToolSetLabels]}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
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
