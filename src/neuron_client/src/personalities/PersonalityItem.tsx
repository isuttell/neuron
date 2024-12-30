import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Pencil, ArrowLeft } from "lucide-react";
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
import { useToast } from "@/hooks/use-toast";
interface PersonalityItemProps {
  personality: Personality;
  className?: string;
}

const PersonalityItem: React.FC<PersonalityItemProps> = ({
  className,
  personality,
}) => {
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonality = useAppSelector(getActivePersonality);
  const isActive = activePersonality?.id === personality.id;
  return (
    <Card
      className={cn(
        "mb-4 flex flex-col",
        className,
        isActive && "border-primary border-2"
      )}
    >
      <CardHeader className="flex flex-row items-center">
        <CardTitle className="text-lg">{personality.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1">
        {personality.logo && (
          <img
            src={personality.logo}
            className="mb-3 rounded-md w-full"
            alt={`${personality.name} logo`}
            width={256}
            height={256}
          />
        )}
        <div className="mb-2 text-xs text-muted-foreground">
          {personality.description}
        </div>
        <div className="flex-1" />
      </CardContent>
      <CardFooter className="flex gap-2 justify-end">
        <EditPersonalityDialog personality={personality} />
        <Button variant="ghost" asChild size="icon">
          <Link
            className="text-foreground"
            to={`/personality/${personality.id}`}
          >
            <Pencil className="size-4" />
          </Link>
        </Button>
        <Button
          variant={isActive ? "default" : "secondary"}
          onClick={() => {
            dispatch(
              setActivePersonality(isActive ? undefined : personality.id)
            );
            navigate(`/`);
            const toastie = toast({
              title: `${personality.name} activated`,
              description: (
                <span
                  onClick={() => {
                    navigate(-1);
                    toastie.dismiss();
                  }}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <ArrowLeft className="size-3.5" /> Go Back
                </span>
              ),
            });
          }}
        >
          {isActive ? "Deactivate" : "Activate"}
        </Button>
      </CardFooter>
    </Card>
  );
};

export default PersonalityItem;
