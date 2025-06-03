import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Pencil, Image } from "lucide-react";
import EditPersonalityDialog from "./EditPersonalityDialog";
import { Personality } from "@/slices/personalitiesSlice.d";
import { Button } from "@/components/ui/button";
import { useAppDispatch, useAppSelector } from "@/hooks";
import {
  setActivePersonality,
  getActivePersonality,
} from "@/slices/personalitiesSlice";
import { updatePersonalityLogo } from "@/actions/personalityActions";
import { cn } from "@/lib/utils";
import { Link, useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { EmbeddingsButton } from "./EmbeddingsButton";

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
  const [isUpdatingLogo, setIsUpdatingLogo] = useState(false);

  const handleActivate = () => {
    dispatch(setActivePersonality(isActive ? undefined : personality.id));
    if (!isActive) {
      toast({
        title: `${personality.name} activated`,
      });
    }
  };

  return (
    <Card
      className={cn("mb-4 flex flex-col", className, isActive && "bg-muted/50")}
    >
      <CardHeader className="flex flex-row items-center">
        <CardTitle className="text-lg">{personality.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 relative">
        {(personality.logo && (
          <img
            src={personality.logo.replace(/\.[^.]+$/, "_t.webp")}
            className={cn(
              "rounded-md w-full cursor-pointer hover:scale-105 transition-all duration-200",
              isUpdatingLogo && "opacity-30"
            )}
            alt={`${personality.name} logo`}
            width={256}
            height={256}
            onClick={() => {
              if (!isActive) {
                handleActivate();
              }
              navigate(`/`);
            }}
          />
        )) || (
          <div
            className={cn(
              "mb-2 text-xs text-muted-foreground",
              isUpdatingLogo && "opacity-30"
            )}
          >
            {personality.description}
          </div>
        )}
        {isUpdatingLogo && (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="size-8 animate-spin" />
          </div>
        )}
      </CardContent>
      <CardFooter className="flex gap-2 justify-end">
        <EmbeddingsButton personalityId={personality.id} />
        <EditPersonalityDialog personality={personality} />
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              disabled={isUpdatingLogo}
              onClick={async () => {
                setIsUpdatingLogo(true);
                try {
                  await dispatch(
                    updatePersonalityLogo(personality.id)
                  ).unwrap();
                  toast({
                    title: "Logo updated",
                    description: "Logo updated successfully",
                  });
                } catch (error) {
                  toast({
                    title: "Failed to update logo",
                    description:
                      error instanceof Error
                        ? error.message
                        : "An unknown error occurred",
                    variant: "destructive",
                  });
                } finally {
                  setIsUpdatingLogo(false);
                }
              }}
            >
              <Image className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Generate Logo</TooltipContent>
        </Tooltip>
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button variant="ghost" asChild size="icon">
              <Link
                className="text-foreground"
                to={`/personality/${personality.id}`}
              >
                <Pencil className="size-4" />
              </Link>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Edit Context</TooltipContent>
        </Tooltip>
        <Button
          variant={isActive ? "default" : "outline"}
          onClick={(e) => {
            e.preventDefault();
            handleActivate();
          }}
        >
          {isActive ? "Deactivate" : "Activate"}
        </Button>
      </CardFooter>
    </Card>
  );
};

export default PersonalityItem;
