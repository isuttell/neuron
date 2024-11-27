import React from "react";
import { Button } from "@/components/ui/button";
import { ListPlus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../hooks";
import { getActivePersonalityId } from "../slices/personalitiesSlice";
import { getActiveProviderId } from "../slices/providersSlice";
import { upsertThread } from "../slices/threadsSlice";
import superagent from "superagent";
import { useNavigate } from "react-router-dom";
const NewThreadButton: React.FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const activeProviderId = useAppSelector(getActiveProviderId);
  return (
    <Button
      variant="secondary"
      className="w-full mb-4"
      onClick={() => {
        superagent
          .post("/api/threads")
          .send({
            personality_id: activePersonalityId,
            provider_id: activeProviderId,
          })
          .then(({ body }) => {
            dispatch(upsertThread(body));
            navigate(`/thread/${body.thread.id}`);
          });
      }}
      disabled={!activePersonalityId || !activeProviderId}
    >
      <ListPlus className="mr-2 h-4 w-4" />
      New Thread
    </Button>
  );
};

export default NewThreadButton;
