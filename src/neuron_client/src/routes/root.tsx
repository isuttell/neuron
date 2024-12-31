import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { useAppSelector } from "../hooks";
import { getConnectionStatus, getSocket } from "../slices/socketSlice";
import { Spinner } from "@/components/ui/spinner";
import { useAppDispatch } from "../hooks";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { MainSidebar } from "@/components/layout/MainSidebar";

export default function Root() {
  const isConnected = useAppSelector(getConnectionStatus);
  const socket = useAppSelector(getSocket);
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch({ type: "socket/connect" });
  }, []);

  return (
    <SidebarProvider>
      <MainSidebar />
      <main className="flex flex-1">
        <SidebarTrigger className="m-2 size-10 mt-4" />
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
    </SidebarProvider>
  );
}
