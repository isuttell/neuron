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
import { Link, useNavigate } from "react-router-dom";

interface PersonalityItemProps {
  personality: Personality;
  className?: string;
}

const PersonalityItem: React.FC<PersonalityItemProps> = ({
  className,
  personality,
}) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
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
        <div className="mb-2">{personality.description}</div>
      </CardContent>
      <CardFooter className="flex gap-2">
        <Button className="w-full" variant="secondary" asChild>
          <Link to={`/personality/${personality.id}`}>Edit Context</Link>
        </Button>
        <Button
          className="w-full"
          variant={isActive ? "default" : "secondary"}
          onClick={() => {
            dispatch(
              setActivePersonality(isActive ? undefined : personality.id)
            );
            navigate(`/`);
          }}
        >
          {isActive ? "Deactivate" : "Activate"}
        </Button>
      </CardFooter>
    </Card>
  );
};

export default PersonalityItem;
