import React from "react";
import { Button } from "@/components/ui/button";
import { ListPlus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { getActiveProviderId } from "../slices/providersSlice";
const NewThreadButton: React.FC = () => {
  const dispatch = useAppDispatch();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activeProviderId = useAppSelector(getActiveProviderId);
  return (
    <Button
      variant="secondary"
      className="w-full mb-4"
      onClick={() => {
        dispatch({
          type: "socket/CreateThread",
          personality_id: activePersonalityId,
          provider_id: activeProviderId,
        });
      }}
      disabled={!activePersonalityId}
    >
      <ListPlus className="mr-2 h-4 w-4" />
      New Thread
    </Button>
  );
};

export default NewThreadButton;
