import React, { useState } from "react";
import { ListPlus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { createThread } from "../actions/threadActions";
import { useNavigate } from "react-router-dom";
import { SidebarGroupAction } from "../components/ui/sidebar";
import { useToast } from "../hooks/use-toast";

const NewThreadButton: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { toast } = useToast();
  const activePersonalityId = useAppSelector(getActivePersonalityId);

  return (
    <SidebarGroupAction
      className="size-6"
      onClick={() => {
        if (!activePersonalityId) {
          return;
        }
        setLoading(true);
        dispatch(createThread({ personalityId: activePersonalityId }))
          .unwrap()
          .then(({ thread }) => {
            navigate(`/thread/${thread.id}`);
          })
          .catch((error) => {
            toast({
              variant: "destructive",
              title: "Failed to create thread",
              description: error?.message || "An unexpected error occurred",
            });
          })
          .finally(() => {
            setLoading(false);
          });
      }}
      disabled={!activePersonalityId || loading}
    >
      <ListPlus className="h-4 w-4" />
    </SidebarGroupAction>
  );
};

export default NewThreadButton;
