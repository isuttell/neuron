import React, { useState } from "react";
import { Loader2, MoreHorizontal, Image, Brain, Play, Square, UserPen, Users, Heart } from "lucide-react";
import {
  Card,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Personality } from "@/slices/personalitiesSlice.d";
import { Button } from "@/components/ui/button";
import { useAppDispatch, useAppSelector } from "@/hooks";
import {
  setActivePersonality,
  getActivePersonality,
} from "@/slices/personalitiesSlice";
import { updatePersonalityLogo } from "@/actions/personalityActions";
import { toggleFavorite } from "@/actions/favoritesActions";
import { isFavorite } from "@/slices/favoritesSlice";
import { cn } from "@/lib/utils";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { usePersonalityPermissions } from "@/hooks/usePersonalityPermissions";
import { isAdmin } from "@/lib/auth";
import { useAuth0 } from "@auth0/auth0-react";
import PersonalityUsersDialog from "@/personalities/PersonalityUsersDialog";

interface PersonalityItemProps {
  personality: Personality;
  className?: string;
}

// Personality dropdown menu with permission-based visibility
const PersonalityDropdownMenu: React.FC<{
  personality: Personality;
  open: boolean;
  setOpen: (open: boolean) => void;
  handleActivate: () => void;
  isActive: boolean;
  setIsUsersDialogOpen: (open: boolean) => void;
  handleUpdateLogo: () => void;
  isUpdatingLogo: boolean;
  handleToggleFavorite: () => void;
  isTogglingFavorite: boolean;
  isPersonalityFavorite: boolean;
}> = ({
  personality,
  open,
  setOpen,
  handleActivate,
  isActive,
  setIsUsersDialogOpen,
  handleUpdateLogo,
  isUpdatingLogo,
  handleToggleFavorite,
  isTogglingFavorite,
  isPersonalityFavorite,
}) => {
  const { user } = useAuth0();
  const { canManage, canManageUsers, canUse } = usePersonalityPermissions(personality.id);
  const isSystemAdmin = isAdmin(user);

  return (
  <div className="absolute top-2 right-2">
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="secondary"
          size="icon"
          className="h-8 w-8 bg-black/70 hover:bg-black/90 text-white shadow-sm backdrop-blur-sm"
        >
          <MoreHorizontal className="size-4" />
          <span className="sr-only">More actions</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {/* Activate/Deactivate - available to everyone */}
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            setOpen(false);
            handleActivate();
          }}
        >
          {isActive ? (
            <>
              <Square className="size-4" />
              Deactivate
            </>
          ) : (
            <>
              <Play className="size-4" />
              Activate
            </>
          )}
        </DropdownMenuItem>

        {/* Favorite/Unfavorite - available to everyone */}
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            setOpen(false);
            handleToggleFavorite();
          }}
          disabled={isTogglingFavorite}
        >
          <Heart className={cn(
            "size-4",
            isPersonalityFavorite ? "fill-current" : "text-muted-foreground"
          )} />
          {isPersonalityFavorite ? "Remove from Favorites" : "Add to Favorites"}
        </DropdownMenuItem>

        {/* Separator if we have admin actions */}
        {(canManage || canManageUsers || isSystemAdmin) && (
          <DropdownMenuSeparator />
        )}

        {/* Edit Personality - personality admins only */}
        {canManage && (
          <DropdownMenuItem asChild>
            <Link
              className="flex items-center gap-2 text-foreground"
              to={`/personality/${personality.id}/edit`}
            >
              <UserPen className="size-4" />
              Edit Personality
            </Link>
          </DropdownMenuItem>
        )}

        {/* Manage Users - personality admins only */}
        {canManageUsers && (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              setOpen(false);
              // Small delay to ensure dropdown closes before dialog opens
              setTimeout(() => setIsUsersDialogOpen(true), 0);
            }}
          >
            <Users className="size-4" />
            Manage Users
          </DropdownMenuItem>
        )}


        {/* Generate Logo - personality admins only */}
        {canManage && (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault();
              setOpen(false);
              handleUpdateLogo();
            }}
            disabled={isUpdatingLogo}
          >
            <Image className="size-4" />
            Generate Logo
          </DropdownMenuItem>
        )}

        {/* View Embeddings - system admins only */}
        {isSystemAdmin && (
          <>
            {(canUse || canManage || canManageUsers) && (
              <DropdownMenuSeparator />
            )}
            <DropdownMenuItem asChild>
              <Link
                className="flex items-center gap-2 text-foreground"
                to={`/personality/${personality.id}/embeddings`}
              >
                <Brain className="size-4" />
                View Embeddings
              </Link>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
  );
};

const PersonalityItem: React.FC<PersonalityItemProps> = ({
  className,
  personality,
}) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const activePersonality = useAppSelector(getActivePersonality);
  const isActive = activePersonality?.id === personality.id;
  const isPersonalityFavorite = useAppSelector(state => isFavorite(state, personality.id));
  const [isUpdatingLogo, setIsUpdatingLogo] = useState(false);
  const [isUsersDialogOpen, setIsUsersDialogOpen] = useState(false);
  const [isTogglingFavorite, setIsTogglingFavorite] = useState(false);
  const [open, setOpen] = useState(false);

  // Handler for dialog open/close with pointer events fix
  const createDialogHandler = (setter: (open: boolean) => void) => {
    return (open: boolean) => {
      setter(open);
      if (!open) {
        // Clear any stuck pointer-events on body
        setTimeout(() => {
          document.body.style.removeProperty('pointer-events');
        }, 100);
      }
    };
  };

  const handleActivate = () => {
    dispatch(setActivePersonality(isActive ? undefined : personality.id));
    if (!isActive) {
      toast(`${personality.name} activated`);
    }
  };

  const handlePersonalityClick = () => {
    dispatch(setActivePersonality(personality.id));
    navigate('/');
  };

  const handleUpdateLogo = async () => {
    setIsUpdatingLogo(true);
    try {
      await dispatch(updatePersonalityLogo(personality.id)).unwrap();
      toast("Logo updated", {
        description: "Logo updated successfully",
      });
    } catch (error) {
      toast.error("Failed to update logo", {
        description:
          error instanceof Error
            ? error.message
            : "An unknown error occurred",
      });
    } finally {
      setIsUpdatingLogo(false);
    }
  };

  const handleToggleFavorite = async () => {
    setIsTogglingFavorite(true);
    try {
      const result = await dispatch(toggleFavorite(personality.id)).unwrap();
      toast(result.added ? "Added to favorites" : "Removed from favorites", {
        description: result.added
          ? `${personality.name} added to favorites`
          : `${personality.name} removed from favorites`,
      });
    } catch (error) {
      toast.error("Failed to update favorite", {
        description:
          error instanceof Error
            ? error.message
            : "An unknown error occurred",
      });
    } finally {
      setIsTogglingFavorite(false);
    }
  };

  return (
    <>
      <Card
        className={cn(
          "mb-4 relative overflow-hidden aspect-square group",
          className,
          isActive && "border-2 border-primary"
        )}
      >
        {/* Logo/Background */}
        <CardContent className="p-0 h-full relative">
          {personality.logo ? (
            <img
              src={personality.logo.replace(/\.[^.]+$/, "_t.webp")}
              className={cn(
                "w-full h-full object-cover cursor-pointer transition-all duration-200 group-hover:scale-105",
                isUpdatingLogo && "opacity-30"
              )}
              alt={`${personality.name} logo`}
              onClick={handlePersonalityClick}
            />
          ) : (
            <div
              className={cn(
                "w-full h-full flex items-center justify-center bg-muted text-center p-4 cursor-pointer",
                isUpdatingLogo && "opacity-30"
              )}
              onClick={handlePersonalityClick}
            >
              <p className="text-xs text-muted-foreground">
                {personality.description}
              </p>
            </div>
          )}

          {/* Loading spinner overlay */}
          {isUpdatingLogo && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/20">
              <Loader2 className="size-8 animate-spin text-white" />
            </div>
          )}
        </CardContent>

        {/* Title overlay */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
          <CardTitle className="text-white text-sm font-bold truncate">
            {personality.name}
          </CardTitle>
        </div>

        {/* Dropdown menu overlay - Permission based */}
        <PersonalityDropdownMenu
          personality={personality}
          open={open}
          setOpen={setOpen}
          handleActivate={handleActivate}
          isActive={isActive}
          setIsUsersDialogOpen={setIsUsersDialogOpen}
          handleUpdateLogo={handleUpdateLogo}
          isUpdatingLogo={isUpdatingLogo}
          handleToggleFavorite={handleToggleFavorite}
          isTogglingFavorite={isTogglingFavorite}
          isPersonalityFavorite={isPersonalityFavorite}
        />

        {/* Active indicator */}
        {isActive && (
          <div className="absolute top-2 left-2">
            <div className="bg-primary text-primary-foreground px-2 py-1 rounded text-xs font-medium h-8 flex items-center">
              Active
            </div>
          </div>
        )}
      </Card>


      {/* Manage Users Dialog */}
      <PersonalityUsersDialog
        personalityId={personality.id}
        open={isUsersDialogOpen}
        onOpenChange={createDialogHandler(setIsUsersDialogOpen)}
        trigger={<></>}
      />
    </>
  );
};

export default PersonalityItem;
