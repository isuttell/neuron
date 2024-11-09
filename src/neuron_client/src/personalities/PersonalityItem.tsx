import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import EditPersonalityDialog from "./EditPersonalityDialog";
import { Personality } from "@/slices/personalitiesSlice";
import { Button } from "@/components/ui/button";
import { useAppDispatch, useAppSelector } from "@/hooks";
import {
  setActivePersonality,
  getActivePersonality,
} from "@/slices/personalitiesSlice";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
interface PersonalityItemProps {
  personality: Personality;
  className?: string;
}

const PersonalityItem: React.FC<PersonalityItemProps> = ({
  className,
  personality,
}) => {
  const dispatch = useAppDispatch();
  const activePersonality = useAppSelector(getActivePersonality);
  const isActive = activePersonality?.id === personality.id;
  return (
    <Card className={cn("mb-4 flex flex-col", className)}>
      <CardHeader className="flex flex-row items-center">
        <CardTitle className="text-xl font-bold">{personality.name}</CardTitle>
        <div className="flex-1" />
        <EditPersonalityDialog personality={personality} />
      </CardHeader>
      <CardContent>
        <div className="mb-2">
          <span className="font-semibold">Context: </span>
          <span>
            {personality.context.trim().length > 0
              ? personality.context.slice(0, 200)
              : "No user instructions"}
          </span>
        </div>
        <div className="">
          <span className="font-semibold">Memory: </span>
          <span>
            {personality.memory.trim().length > 0
              ? personality.memory
              : "No memories"}
          </span>
        </div>
      </CardContent>
      <CardFooter className="flex gap-2">
        <Button className="w-full" variant="secondary" asChild>
          <Link to={`/personality/${personality.id}`}>Edit</Link>
        </Button>
        <Button
          className="w-full"
          variant={isActive ? "default" : "secondary"}
          onClick={() => {
            dispatch(
              setActivePersonality(isActive ? undefined : personality.id)
            );
            if (!isActive) {
              dispatch({
                type: "socket/GetThreads",
                personality_id: personality.id,
              });
            }
          }}
        >
          {isActive ? "Deactivate" : "Activate"}
        </Button>
      </CardFooter>
    </Card>
  );
};

export default PersonalityItem;
