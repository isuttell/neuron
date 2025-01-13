import { useEffect } from "react";
import { useAppSelector } from "../hooks";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getPersonalities } from "../slices/personalitiesSlice";
import PersonalityItem from "../personalities/PersonalityItem";
import EditPersonalityDialog from "../personalities/EditPersonalityDialog";
import { useAppDispatch } from "../hooks";
import { fetchPersonalities } from "../actions/personalityActions";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  getPersonalitiesLoading,
  getPersonalitiesError,
} from "../slices/personalitiesSlice";
import { Spinner } from "@/components/ui/spinner";

export default function Personalities() {
  const personalities = useAppSelector(getPersonalities);
  const loading = useAppSelector(getPersonalitiesLoading);
  const error = useAppSelector(getPersonalitiesError);
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(fetchPersonalities());
  }, []);

  if (loading && personalities.length < 1) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-2xl font-bold">Personalities</h1>
        <div className="flex-1" />
        <EditPersonalityDialog />
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {personalities
            .slice()
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((personality) => (
              <PersonalityItem key={personality.id} personality={personality} />
            ))}
        </div>
      </ScrollArea>
    </div>
  );
}
