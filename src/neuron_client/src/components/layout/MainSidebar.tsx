import { Home, CircleUser, GalleryThumbnails, FileText } from "lucide-react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
} from "@/components/ui/sidebar";
import NavThreads from "@/threads/NavThreads";
import logo from "@/assets/logo.svg";

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
  return (
    <Sidebar>
      <SidebarHeader className="border-b">
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
    </Sidebar>
  );
}
