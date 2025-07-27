import logo from "@/assets/logo.svg";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import ImageContent from "@/messages/ImageContent";
import NavThreads from "@/threads/NavThreads";
import FavoritePersonalities from "@/components/sidebar/FavoritePersonalities";
import {
  Calendar,
  ChevronUp,
  CircleUser,
  FileText,
  HelpCircle,
  Home,
  LayoutGrid,
  LogOut,
  Shield,
} from "lucide-react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { AspectRatio } from "@/components/ui/aspect-ratio";
import { useAppSelector } from "@/hooks";
import { usePermissions } from "@/hooks/usePermissions";
import { getSidebarImage } from "@/slices/appSlice";
import { useAuth0 } from "@auth0/auth0-react";
import { LucideIcon } from "lucide-react";
import { ProvidersMenuItem } from "./ProvidersMenuItem";

interface SidebarLink {
  to: string;
  label: string;
  Icon: LucideIcon;
  onClick?: () => void;
}

export function MainSidebar() {
  const location = useLocation();
  const { logout, user } = useAuth0();
  const sidebarImage = useAppSelector(getSidebarImage);
  const { canAccessPrompts, canAccessProviders, isAdmin } = usePermissions();
  const links: SidebarLink[] = [
    {
      to: "/",
      label: "Home",
      Icon: Home,
    },
    {
      to: "/personalities",
      label: "Personalities",
      Icon: CircleUser,
    },
    ...(isAdmin ? [{
      to: "/gallery",
      label: "Recent Media",
      Icon: LayoutGrid,
    }] : []),
    // Disabled since it's broken and not used
    // {
    //   to: "/media-lists",
    //   label: "Media Lists",
    //   Icon: List,
    // },
  ];

  return (
    <Sidebar className="z-50">
      <SidebarHeader className="border-b ipad-sidebar-spacing">
        <AspectRatio
          ratio={1}
          className="flex justify-center rounded-lg bg-muted items-center m-2"
        >
          <ImageContent
            url={sidebarImage || `/static/smart_dashboard_image.png`}
            width={256}
            height={256}
          />
        </AspectRatio>
        <div>
          <Link
            to="/"
            className="flex items-center gap-2 font-semibold px-2 py-2 text-white hover:text-white/80"
          >
            <img src={logo} alt="Neuron" className="size-6 -ml-1" />
            <span>Neuron</span>
          </Link>
        </div>
        <SidebarMenu>
          {links.map((link) => (
            <SidebarMenuItem key={link.to}>
              <SidebarMenuButton
                isActive={location.pathname === link.to}
                asChild={!link.onClick}
                onClick={link.onClick && (() => link.onClick?.())}
              >
                {link.onClick ? (
                  <div className="flex items-center gap-2 text-gray-300">
                    <link.Icon className="h-4 w-4" />
                    <span>{link.label}</span>
                  </div>
                ) : (
                  <NavLink to={link.to} className="text-gray-300 ">
                    <link.Icon className="h-4 w-4" />
                    <span>{link.label}</span>
                  </NavLink>
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
        <FavoritePersonalities className="mt-0" />
      </SidebarHeader>

      <SidebarContent>

        <NavThreads activePathname={location.pathname} />
      </SidebarContent>
      <SidebarFooter className="border-t">
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton>
                  <img
                    src={user?.picture}
                    alt={user?.nickname}
                    className="size-6 rounded-full"
                  />
                  <div className="flex flex-col">{user?.nickname}</div>
                  <ChevronUp className="ml-auto" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>

              <DropdownMenuContent
                side="top"
                className="w-[--radix-popper-anchor-width]"
              >
                <div className="flex items-center gap-2 p-2 border-b">
                  <img
                    src={user?.picture}
                    alt={user?.nickname}
                    className="size-8 rounded-full"
                  />
                  <div className="flex flex-col">
                    <div className="text-sm font-semibold">
                      {user?.nickname}
                    </div>
                    <div className="text-xs text-gray-500">{user?.email}</div>
                  </div>
                </div>
                {canAccessPrompts && (
                  <DropdownMenuItem asChild>
                    <NavLink
                      to="/prompts"
                      className="text-gray-300 hover:text-accent-foreground flex items-center gap-2 block"
                    >
                      <FileText className="h-4 w-4" />
                      <span>Prompts</span>
                    </NavLink>
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem asChild>
                  <NavLink
                    to="/scheduled"
                    className="text-gray-300 hover:text-accent-foreground flex items-center gap-2"
                  >
                    <Calendar className="h-4 w-4" />
                    <span>Scheduled</span>
                  </NavLink>
                </DropdownMenuItem>
                {canAccessProviders && (
                  <ProvidersMenuItem className="text-gray-300 hover:text-accent-foreground flex items-center gap-2" />
                )}
                <DropdownMenuItem asChild>
                  <NavLink
                    to="/help"
                    className="text-gray-300 hover:text-accent-foreground flex items-center gap-2"
                  >
                    <HelpCircle className="h-4 w-4" />
                    <span>Help</span>
                  </NavLink>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <NavLink
                    to="/privacy"
                    className="text-gray-300 hover:text-accent-foreground flex items-center gap-2"
                  >
                    <Shield className="h-4 w-4" />
                    <span>Privacy</span>
                  </NavLink>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    logout();
                  }}
                  className="flex items-center gap-2"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
