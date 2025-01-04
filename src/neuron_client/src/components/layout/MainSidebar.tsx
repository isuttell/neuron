import { Home, CircleUser, GalleryThumbnails, FileText } from "lucide-react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarFooter,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import NavThreads from "@/threads/NavThreads";
import logo from "@/assets/logo.svg";
import ImageContent from "@/messages/ImageContent";
import { ChevronUp } from "lucide-react";

import { useAuth0 } from "@auth0/auth0-react";
import { getSidebarImage } from "@/slices/appSlice";
import { useAppSelector } from "@/hooks";

const links = [
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
  {
    to: "/gallery",
    label: "Gallery",
    Icon: GalleryThumbnails,
  },
  {
    to: "/prompts",
    label: "Prompts",
    Icon: FileText,
  },
];

export function MainSidebar() {
  const location = useLocation();
  const { logout, user } = useAuth0();

  const sidebarImage = useAppSelector(getSidebarImage);
  return (
    <Sidebar>
      <SidebarHeader className="border-b">
        <div className="flex justify-center items-center p-2">
          <ImageContent
            url={sidebarImage || `/static/smart_dashboard_image.png`}
            width={256}
            height={256}
          />
        </div>
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
                asChild
              >
                <NavLink to={link.to} className="text-gray-300">
                  <link.Icon className="h-4 w-4" />
                  <span>{link.label}</span>
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
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

                <DropdownMenuItem
                  onClick={() => {
                    logout();
                  }}
                >
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
