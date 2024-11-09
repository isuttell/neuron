import {
  CircleUser,
  Package2,
  Brain,
  GalleryThumbnails,
  ChartBar,
} from "lucide-react";
import { useEffect } from "react";
import { Outlet, Link, NavLink } from "react-router-dom";
import { useAppSelector } from "../hooks";
import { getConnectionStatus, getSocket } from "../slices/socketSlice";
import { Spinner } from "@/components/ui/spinner";
import { useAppDispatch } from "../hooks";
import NavThreads from "../threads/NavThreads";

const links = [
  {
    to: "/",
    label: "Personalities",
    Icon: CircleUser,
  },
  {
    to: "/providers",
    label: "Providers",
    Icon: Brain,
  },
  {
    to: "/gallery",
    label: "Gallery",
    Icon: GalleryThumbnails,
  },
  {
    to: "/stats",
    label: "Stats",
    Icon: ChartBar,
  },
];

export default function Root() {
  const isConnected = useAppSelector(getConnectionStatus);
  const socket = useAppSelector(getSocket);
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch({ type: "socket/connect" });
  }, []);

  return (
    <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
      <div className="hidden border-r bg-muted/40 md:block">
        <div className="flex h-full max-h-screen flex-col gap-2">
          <div className="flex h-14 items-center border-b px-4 lg:h-[60px] lg:px-6">
            <Link
              to="/"
              className="flex text-white items-center gap-2 font-semibold"
            >
              <Package2 className="h-6 w-6" />
              <span className="">Neuron</span>
            </Link>
          </div>
          <div className="flex-1 flex flex-col overflow-y-auto">
            <nav className="grid items-start px-2 text-sm font-medium lg:px-4">
              {links.map((link) => (
                <NavLink
                  end
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2 transition-all  hover:text-primary ${
                      isActive
                        ? "text-primary bg-muted"
                        : "text-muted-foreground"
                    }`
                  }
                  to={link.to}
                  key={link.to}
                >
                  <link.Icon className="h-4 w-4" />
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <NavThreads />
          </div>
        </div>
      </div>
      <main className="flex">
        {isConnected && socket ? (
          <Outlet />
        ) : (
          <div className="flex flex-1 items-center justify-center h-full">
            <div className="flex flex-col items-center gap-2">
              <Spinner />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
