import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { ListPlus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { createThread } from "../actions/threadActions";
import { useNavigate } from "react-router-dom";

const NewThreadButton: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);

  return (
    <Button
      variant="secondary"
      className="w-full mb-4"
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
          .finally(() => {
            setLoading(false);
          });
      }}
      disabled={!activePersonalityId || loading}
    >
      <ListPlus className="mr-2 h-4 w-4" />
      New Thread
    </Button>
  );
};

export default NewThreadButton;
