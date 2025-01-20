import { Settings } from "lucide-react";
import { NavLink } from "react-router-dom";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { withAdminAuth } from "@/components/hoc/withAdminAuth";
import { cn } from "@/lib/utils";

function ProvidersMenuItemBase({ className }: { className?: string }) {
  return (
    <DropdownMenuItem asChild>
      <NavLink to="/providers" className={cn(className)}>
        <Settings className="h-4 w-4" />
        <span>Providers</span>
      </NavLink>
    </DropdownMenuItem>
  );
}

export const ProvidersMenuItem = withAdminAuth(ProvidersMenuItemBase);
